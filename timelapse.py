import argparse
import ctypes
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from datetime import datetime

import cv2
import numpy as np


DEFAULT_URL = "http://192.168.1.5:8080/video"


def default_output_dir():
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "timelapses")
    return "timelapses"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Record a timelapse from an IP webcam in the background."
    )
    parser.add_argument("--record", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--parent-pid", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--stop-file", default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Stream URL (e.g. http://<phone-ip>:8080/video)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=600.0,
        help="Timelapse speed multiplier (600 = 1 output second per 10 real minutes).",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=30.0,
        help="Frames per second of the output video.",
    )
    parser.add_argument(
        "--output",
        default=default_output_dir(),
        help="Folder where videos are saved.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Optional: record for this many seconds, then stop.",
    )
    return parser.parse_args()


def parent_alive(pid):
    if pid is None:
        return True
    if os.name == "nt":
        SYNCHRONIZE = 0x00100000
        WAIT_TIMEOUT = 0x00000102
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            return False
        result = ctypes.windll.kernel32.WaitForSingleObject(handle, 0)
        ctypes.windll.kernel32.CloseHandle(handle)
        return result == WAIT_TIMEOUT
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def open_stream(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "IPWebcamTimelapse/1.0"})
        stream = urllib.request.urlopen(req, timeout=15)
        buf = b""
        deadline = time.time() + 15
        while time.time() < deadline:
            chunk = stream.read(65536)
            if not chunk:
                break
            buf += chunk
            start = buf.find(b"\xff\xd8")
            end = buf.find(b"\xff\xd9", start + 2) if start != -1 else -1
            if start != -1 and end != -1:
                frame = cv2.imdecode(
                    np.frombuffer(buf[start:end + 2], dtype=np.uint8),
                    cv2.IMREAD_COLOR,
                )
                if frame is not None:
                    return "raw", stream, frame
        stream.close()
    except Exception:
        pass
    cap = cv2.VideoCapture(url)
    if cap.isOpened():
        ok, frame = cap.read()
        if ok and frame is not None:
            return "cv", cap, frame
    raise SystemExit(f"Could not open stream: {url}")


def make_writer(path, fps, width, height):
    attempts = [("avc1", ".mp4"), ("mp4v", ".mp4"), ("MJPG", ".avi")]
    for codec, ext in attempts:
        candidate = os.path.splitext(path)[0] + ext
        writer = cv2.VideoWriter(
            candidate, cv2.VideoWriter_fourcc(*codec), fps, (width, height)
        )
        if writer.isOpened():
            return writer, candidate
        writer.release()
    raise SystemExit("Could not create output video writer (no supported codec).")


def record(args):
    capture_interval = args.speed / args.fps
    mode, src, first_frame = open_stream(args.url)

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(
        args.output, f"timelapse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    )

    stop_event = threading.Event()
    frame_lock = threading.Lock()
    latest = first_frame
    stream_ok = True
    rstate = {"writer": None, "path": None, "frames": 0}

    def reader():
        nonlocal latest, stream_ok
        if mode == "raw":
            buf = b""
            while not stop_event.is_set():
                while True:
                    s = buf.find(b"\xff\xd8")
                    if s != -1:
                        e = buf.find(b"\xff\xd9", s + 2)
                        if e != -1:
                            jpg = buf[s:e + 2]
                            buf = buf[e + 2:]
                            frame = cv2.imdecode(
                                np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR
                            )
                            if frame is not None:
                                with frame_lock:
                                    latest = frame
                            break
                    try:
                        chunk = src.read(65536)
                    except Exception:
                        stream_ok = False
                        return
                    if not chunk:
                        stream_ok = False
                        return
                    buf += chunk
                    if len(buf) > 4_000_000:
                        idx = buf.rfind(b"\xff\xd8")
                        buf = buf[idx:] if idx != -1 else b""
        else:
            while not stop_event.is_set():
                ok, frame = src.read()
                if not ok:
                    time.sleep(0.02)
                    continue
                with frame_lock:
                    latest = frame

    def writer_loop():
        next_capture = None
        while not stop_event.is_set():
            with frame_lock:
                f = latest
            if f is None:
                time.sleep(0.05)
                continue
            now = time.time()
            if rstate["writer"] is None:
                height, width = f.shape[:2]
                rstate["writer"], rstate["path"] = make_writer(
                    out_path, args.fps, width, height
                )
                rstate["writer"].write(f)
                rstate["frames"] += 1
                next_capture = now + capture_interval
            elif now >= next_capture:
                rstate["writer"].write(f)
                rstate["frames"] += 1
                next_capture += capture_interval
            time.sleep(0.02)
        if rstate["writer"] is not None:
            rstate["writer"].release()

    reader_thread = threading.Thread(target=reader, daemon=True)
    writer_thread = threading.Thread(target=writer_loop, daemon=True)
    reader_thread.start()
    writer_thread.start()

    start = time.time()
    while not stop_event.is_set():
        if args.duration is not None and time.time() - start >= args.duration:
            break
        if args.stop_file and os.path.exists(args.stop_file):
            break
        if args.parent_pid is not None and not parent_alive(args.parent_pid):
            break
        if not stream_ok:
            break
        time.sleep(0.1)

    stop_event.set()
    writer_thread.join(timeout=5)
    reader_thread.join(timeout=2)
    if mode == "raw":
        try:
            src.close()
        except Exception:
            pass
    elif not reader_thread.is_alive():
        src.release()
    if args.stop_file:
        try:
            os.remove(args.stop_file)
        except OSError:
            pass

    elapsed = max(time.time() - start, 1e-9)
    print(f"Saved {rstate['path'] or out_path}")
    print(
        f"{rstate['frames']} frames recorded over {elapsed:.0f}s at {args.fps:g} fps "
        f"-> {args.speed:g}x timelapse"
    )


def gui():
    import tkinter as tk
    from tkinter import messagebox, ttk
    import threading

    root = tk.Tk()
    root.title("IP Webcam Timelapse Recorder")
    root.resizable(False, False)

    url_var = tk.StringVar(value=DEFAULT_URL)
    speed_var = tk.StringVar(value="600")
    status_var = tk.StringVar(value="Enter your camera URL and speed, then press Start.")

    frame = ttk.Frame(root, padding=14)
    frame.grid(row=0, column=0, sticky="nsew")

    ttk.Label(
        frame,
        text="IP Webcam Timelapse",
        font=("Segoe UI", 12, "bold"),
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

    ttk.Label(
        frame,
        text="Stream URL (from the IP Webcam app, e.g. "
        "http://192.168.1.5:8080/video):",
        wraplength=360,
    ).grid(row=1, column=0, columnspan=2, sticky="w")
    ttk.Entry(frame, textvariable=url_var, width=48).grid(
        row=2, column=0, columnspan=2, sticky="we", pady=(2, 8)
    )

    ttk.Label(frame, text="Timelapse speed (x):").grid(row=3, column=0, sticky="w")
    ttk.Entry(frame, textvariable=speed_var, width=12).grid(
        row=3, column=1, sticky="w", pady=(0, 8)
    )

    start_btn = ttk.Button(frame, text="Start", width=20)
    start_btn.grid(row=4, column=0, sticky="w")

    stop_btn = ttk.Button(frame, text="Stop", width=10, state="disabled")
    stop_btn.grid(row=4, column=1, sticky="w")

    ttk.Separator(frame).grid(row=5, column=0, columnspan=2, sticky="we", pady=10)

    ttk.Label(frame, textvariable=status_var, wraplength=360).grid(
        row=6, column=0, columnspan=2, sticky="w"
    )

    state = {"proc": None, "stop_file": None}

    def watch(proc):
        lines = []
        while True:
            line = proc.stdout.readline()
            if line:
                lines.append(line.strip())
            elif proc.poll() is not None:
                break

        def done():
            start_btn.config(state="normal")
            stop_btn.config(state="disabled")
            state["proc"] = None
            if proc.returncode == 0:
                saved = next((l for l in lines if l.startswith("Saved")), None)
                status_var.set(saved if saved else "Finished.")
            else:
                meaningful = [
                    l
                    for l in lines
                    if l and not l.startswith("usage") and not l.startswith(" ")
                ]
                status_var.set(
                    "Failed: " + (meaningful[-1] if meaningful else "unknown error")
                )

        root.after(0, done)

    def start():
        url = url_var.get().strip()
        speed = speed_var.get().strip()
        if not url:
            messagebox.showerror("Missing URL", "Please enter your camera stream URL.")
            return
        try:
            speed_f = float(speed)
        except ValueError:
            messagebox.showerror("Invalid number", "Speed must be a number.")
            return

        stop_file = os.path.join(
            tempfile.gettempdir(),
            f"iptl_stop_{os.getpid()}_{int(time.time() * 1000)}.flag",
        )
        try:
            os.remove(stop_file)
        except OSError:
            pass
        state["stop_file"] = stop_file

        if getattr(sys, "frozen", False):
            cmd = [
                sys.executable,
                "--record",
                "--url",
                url,
                "--speed",
                str(speed_f),
                "--parent-pid",
                str(os.getpid()),
                "--stop-file",
                stop_file,
            ]
        else:
            cmd = [
                sys.executable,
                sys.argv[0],
                "--record",
                "--url",
                url,
                "--speed",
                str(speed_f),
                "--parent-pid",
                str(os.getpid()),
                "--stop-file",
                stop_file,
            ]

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
        )
        state["proc"] = proc
        start_btn.config(state="disabled")
        stop_btn.config(state="normal")
        status_var.set("Recording in the background... press Stop to finish and save.")
        threading.Thread(target=watch, args=(proc,), daemon=True).start()

    def stop_recording():
        proc = state["proc"]
        stop_file = state["stop_file"]
        if proc is not None and proc.poll() is None and stop_file:
            try:
                open(stop_file, "w").close()
            except Exception:
                pass
            status_var.set("Stopping... saving video...")
            stop_btn.config(state="disabled")

    def on_close():
        stop_recording()
        root.destroy()

    start_btn.config(command=start)
    stop_btn.config(command=stop_recording)
    root.protocol("WM_DELETE_WINDOW", on_close)

    root.mainloop()


def main():
    args = parse_args()
    config_flags = {"--url", "--speed", "--fps", "--output", "--duration"}
    explicit = bool(set(sys.argv[1:]) & config_flags)
    if args.record or explicit:
        record(args)
    else:
        gui()


if __name__ == "__main__":
    main()