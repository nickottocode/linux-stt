import time
from websockets.exceptions import ConnectionClosedOK
import asyncio
import json
import websockets
import pyaudio
import os
import argparse
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger("usemicrophone")


load_dotenv("/home/notto/workspace/repos/linux-stt/.env")


def configure_logger(loglevel):
    debugdict = dict(
        DEBUG=logging.DEBUG,
        INFO=logging.INFO,
        WARNING=logging.WARNING,
        ERROR=logging.ERROR,
    )
    logger.setLevel(debugdict[loglevel])
    formatter = logging.Formatter("%(levelname)-8s %(asctime)s %(name)-12s %(message)s")
    streamhandle = logging.StreamHandler()
    streamhandle.setFormatter(formatter)
    logger.addHandler(streamhandle)
    # Re-enable the FileHandler if you want to see the logs
    # filehandle = logging.FileHandler(
    # "/full/path/to/linux-stt/logs.log"
    # )
    # filehandle.setFormatter(formatter)
    # logger.addHandler(filehandle)


FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
TIME_LIMIT = 15  # time limit in seconds

frames = []
recv_messages = []


def _handle_task_result(task):
    try:
        task.result()
    except asyncio.CancelledError:
        pass  # Task cancellation should not be logged as an error.
    except Exception:  # pylint: disable=broad-except
        logger.error("Exception raised by task = %r", task)


async def start_stream(mic_stream, uri):
    """Run websocket connection to stream audio file to uri.

    Parameters
    ----------
    mic_stream: pyaudio.Stream object
    uri: string
        The full destination with request parameters baked in

    """
    extra_headers = {"Authorization": f"Token {os.getenv('DEEPGRAM_API_KEY')}"}
    if "?" in uri:
        uri = f"{uri}&encoding=linear16&sample_rate={RATE}&channels={CHANNELS}"
    else:
        uri = f"{uri}?encoding=linear16&sample_rate={RATE}&channels={CHANNELS}"
    logger.debug(uri)
    try:
        async with websockets.connect(uri, extra_headers=extra_headers) as ws:
            # see https://websockets.readthedocs.io/en/stable/reference/client.html#websockets.client.WebSocketClientProtocol
            shared_data = {"endstream": False}
            requestid = ws.response_headers.get("dg-request-id", ws.response_headers)
            logger.debug(f"Request: {requestid}")

            async def sender(mic_stream, ws, shared):
                """Send audio through websocket."""
                while True:
                    now = time.time()
                    piece = mic_stream.read(mic_stream.get_read_available())

                    if shared_data["endstream"]:
                        piece = b""  # This will close the connection
                        logger.debug("Sending close frame")
                        await ws.send(piece)
                        break
                    elif len(piece) == 0:
                        continue

                    try:
                        frames.append(piece)
                        await ws.send(piece)
                    except ConnectionClosedOK:
                        break

                    await asyncio.sleep(0.01)

            # This example function will handle responses.
            async def receiver(ws, shared):
                async for msg in ws:
                    # Deserialize the JSON message.
                    msg = json.loads(msg)
                    if msg.get("type", "") == "UtteranceEnd":
                        logger.info(msg)
                        continue
                    try:
                        transcript = (
                            msg.get("channel").get("alternatives")[0].get("transcript")
                        )
                        final = msg.get("is_final")
                        speech_final = msg.get("speech_final")
                        if final:
                            logger.debug(
                                f"{transcript}, is_final {final}, speech_final {speech_final}"
                            )
                            if len(transcript.strip()) > 0:
                                if "exit" in transcript.lower():
                                    last_pos = transcript.lower().rfind("exit")
                                    transcript = transcript[:last_pos]
                                    shared["endstream"] = True
                                print(f"{transcript}")
                    except Exception as e:
                        # The above get will fail on final metadata response
                        logger.error(f"Transcript processing error {e}")
                    if msg.get("channel", False):
                        recv_messages.append(msg)

            loop = asyncio.get_event_loop()
            sendertask = loop.create_task(sender(mic_stream, ws, shared_data))
            receivertask = loop.create_task(receiver(ws, shared_data))
            sendertask.add_done_callback(_handle_task_result)
            receivertask.add_done_callback(_handle_task_result)
            await asyncio.wait([sendertask, receivertask], timeout=None)
    except Exception as e:
        logger.error(f"Exception: {e}")
        logger.error(f"Dir: {dir(e)}")
        logger.error(f"Headers: {e.headers}")


def stream_microphone(mic_stream, uri):
    asyncio.run(start_stream(mic_stream, uri))


if __name__ == "__main__":

    parser = argparse.ArgumentParser("microphone")
    parser.add_argument("url", help="The URL to hit", type=str)
    parser.add_argument(
        "--loglevel", help="The logging level", type=str, default="INFO"
    )
    args = parser.parse_args()
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True)

    configure_logger(args.loglevel)

    try:
        stream_microphone(stream, args.url)
    except Exception as e:
        logger.error(f"Found exception {e}")
    finally:
        stream.close()
    transcript = ""
    for msg in recv_messages:
        if "channel" in msg:
            if msg.get("is_final", False):
                transcript = (
                    transcript.strip()
                    + " "
                    + msg["channel"]["alternatives"][0]["transcript"]
                )

    # print(transcript) # There are two print-statements in this file.  Swap them out to print either streaming, or at the end.
