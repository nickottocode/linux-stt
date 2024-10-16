
while IFS= read -r newline; do
    echo $newline | tr '\n' ' ' | xclip -selection clipboard && xdotool key Control_L+v  ;
done < <(python3 -u /full/path/to/linux-stt/microphone.py "wss://api.deepgram.com/v1/listen?model=nova-2-general&smart_format=true")
