# IPLapse

Records a time-lapse video from your phone's IP webcam in the background. You provide the stream link and the speed, and it quietly records until you press Stop. No preview window, no clutter.

## What you need

- A phone running the **IP Webcam** app (or any camera that serves an MJPEG stream URL).
- Your PC and phone on the same Wi-Fi network.

## Installation

**Option 1 — Installer (recommended):**

Run **`IPLapse-Setup.exe`** (in the `installer` folder) and follow the wizard. It installs IPLapse with Start Menu and (optional) desktop shortcuts, plus an uninstaller.

To uninstall later, use **Settings → Apps → IPLapse**, or run `unins000.exe` from the install folder.

**Option 2 — Portable:**

Double-click **`IPWebcamTimelapse.exe`** (in the `dist` folder). No install needed.

## Get your stream URL

1. Open the IP Webcam app on your phone.
2. Tap **Start server** at the bottom.
3. The app shows an address like `http://192.168.1.5:8080` — your stream URL is that address + `/video`:

```
http://192.168.1.5:8080/video
```

## How to use

1. Launch IPLapse (from the Start Menu, desktop shortcut, or the EXE).
2. Paste your stream URL into the **Stream URL** box.
3. Enter a **speed** (see below).
4. Press **Start**. The link is tested first — if it can't be reached, you'll see an error with troubleshooting hints and recording won't start.
5. Press **Stop** (or close the window) when done. The video is saved automatically.

Videos are saved in **`Videos\IPLapse`** in your user folder, named like:

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

**"Could not open stream" / invalid link**
IPLapse tests your link before recording and refuses invalid ones. Check that:
- the URL ends in `/video` (e.g. `http://192.168.1.5:8080/video`),
- the IP Webcam app is on **Start server**,
- your PC and phone are on the same Wi-Fi network,
- your PC's firewall allows the connection.

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

To build the installer (requires [Inno Setup 6](https://jrsoftware.org/isinfo.php)):

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" IPLapse.iss
```

The installer is output to the `installer` folder as `IPLapse-Setup.exe`.