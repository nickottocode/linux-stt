# linux-stt

One of the things that always bothered me being a Linux user is that some features that are very easy to do on a phone are challenging to figure out how to do on a computer.
In particular, I could dictate a Slack message on my phone, but for the life of me could not figure out how to dictate a Slack message on my laptop.
As a matter of fact, unless the dictation feature came within the app itself, dictation seemed to be a tool that was simply unavailable on Linux more broadly.
Of course, I knew that wasn't true, there had to be a way.
I finally figured it out!

My primary requirement was, when pressing a custom shortcut key, I wanted to be able to dictate in real time without waiting until the end of my monologue to see the results.
This means the audio needs to be streamed to a speech provider (of course we're going to use Deepgram here) but it also means that the Linux script needs to be able to paste the output from Deepgram into the currently open input field.
The two commands to grab text and paste are `xclip` and `xdotool` like:
```sh
echo "some text" | xclip -selection clipboard && xdotool key Control_L+v
```

The next challenge is getting the system to output the text in real time.
Linux could quite easily process streams of text but I had issues getting that to work without using a terminal emulator.
Since `gnome-terminal` doesn't have an obvious flag to hide the terminal on startup, I opted for `terminator` which makes that super easy.


# Setup
1. Clone this repo.
2. In Settings->Keyboard->Custom Shortcuts (may be named differently in your Linux flavor):
  - Add a custom shortcut (give it any name you like)
  - For the `command` give it:
```sh
terminator -H -e  "bash -c /full/path/to/linux-stt/speechtotext.sh; exit"
```
  - Add a hotkey.  I have mine mapped to `<super> + M` for "microphone"
3. Add a `.env` file with the `DEEPGRAM_API_KEY` defined.
  - No, it won't be able to read from your system environment variables.
4. Update the script `speechtotext.sh` with the full paths to your location



# Limitations
- Requires a control word to quit - currently this is "exit".  This doesn't have to be the way.  Check out [linux-voice-type](https://github.com/Jeremie-Chauvel/linux-voice-type/tree/main) for an example of using the custom shortcut key twice - once to start and once to stop.  I kind of like the "exit" control word, but it's not for everyone.