# IP Webcam Timelapse Recorder

Records a time-lapse video from your phone's IP webcam in the background.You provide the stream link and the speed, and it quietly records until you press Stop.

## What you need

- A phone running the **IP Webcam** app (or any camera that serves an MJPEG stream URL).
- Your PC and phone on the same Wi-Fi network.

## Get your stream URL

1. Open the IP Webcam app on your phone.
2. Tap **Start server** at the bottom.
3. The app shows an address like `http://192.168.1.5:8080` — your stream URL is that address + `/video`:

```
http://192.168.1.5:8080/video
```

## How to use

1. Double-click **`IPWebcamTimelapse.exe`** (in the `dist` folder).
2. Paste your stream URL into the **Stream URL** box.
3. Enter a **speed** (see below).
4. Press **Start** — it records in the background.
5. Press **Stop** (or close the window) when done. The video is saved automatically.

Videos are saved in the **`timelapses`** folder next to the EXE, named like:

```
timelapse_20260101_153000.mp4
```

## What "speed" means

The speed is how much faster the time-lapse plays than real time:

| Speed | 1 second of video covers |
|-------|--------------------------|
| 30x   | 30 seconds              |
| 300x  | 5 minutes               |
| 600x  | 10 minutes              |
| 1200x | 20 minutes              |

A camera frame is captured every `speed / 30` seconds (30 = output frames per second).

## Output format

- **H.264 MP4** — plays natively in Windows Movies & TV, Photos, and VLC.

## Troubleshooting

**"Could not open stream"**
Double-check the URL ends in `/video`, the app is on **Start server**, and both devices are on the same network. Make sure your PC's firewall allows the connection.

**Preview/video looks choppy or slow**
The camera app decodes video with your PC's CPU. Lower the **resolution** in the IP Webcam app (buttons on the phone screen) for smoother performance.

## Building from source

```bash
pip install -r requirements.txt
python timelapse.py              # opens the GUI
```

To build the EXE yourself:

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name IPWebcamTimelapse timelapse.py
```