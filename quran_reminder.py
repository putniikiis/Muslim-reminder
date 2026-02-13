#!/usr/bin/env python3
"""Quran Reminder — аят по горячей клавише и раз в час. Linux и macOS."""

import json
import os
import random
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from urllib.parse import urlencode

from pynput import keyboard


IS_MAC = sys.platform == "darwin"

if not IS_MAC and hasattr(os, "getuid"):
    _uid = os.getuid()
    _runtime = f"/run/user/{_uid}"
    if not os.environ.get("DBUS_SESSION_BUS_ADDRESS") and os.path.isfile(f"{_runtime}/bus"):
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={_runtime}/bus"
    if not os.environ.get("XDG_RUNTIME_DIR") and os.path.isdir(_runtime):
        os.environ["XDG_RUNTIME_DIR"] = _runtime
    if not os.environ.get("DISPLAY"):
        os.environ["DISPLAY"] = ":0"


DEBOUNCE_SEC = 2
REMINDER_INTERVAL_SEC = 3600
_notify_lock = threading.Lock()
_last_activate_time = 0.0
_hourly_timer = None

API_BASE = "https://api.quran.com/api/v3"
TRANSLATION_ID_RU = 45
RECITER = "Muhammad_Ayyoub_128kbps"
EVERYAYAH_BASE = "https://everyayah.com/data"
UA = "Mozilla/5.0 (compatible; QuranReminder/1.0)"

CHAPTER_VERSES = [
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128,
    111, 110, 98, 135, 112, 78, 118, 64, 77, 227, 93, 88, 69, 60, 34, 30, 73,
    54, 45, 83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38, 29, 18, 45, 60,
    49, 62, 55, 78, 96, 29, 22, 24, 13, 14, 11, 11, 18, 12, 12, 30, 52, 52,
    44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42, 29, 19, 36, 25, 22, 17, 19,
    26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8, 11, 11, 8, 3, 9, 5, 4, 7, 3,
    6, 3, 5, 4, 5, 6,
]


def show_notification(title: str, message: str) -> None:
    env = os.environ.copy()
    msg_clean = message.replace("\\", "\\\\").replace('"', "'")[:500]
    title_clean = title.replace("\\", "\\\\").replace('"', "'")
    if IS_MAC:
        try:
            subprocess.run(
                ["osascript", "-e", f'display notification "{msg_clean}" with title "{title_clean}"'],
                env=env,
                timeout=5,
                check=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            print(f"📖 {title}\n{message}\n")
    else:
        try:
            subprocess.run(
                ["notify-send", "-t", "12000", "-u", "normal", title, message],
                env=env,
                timeout=5,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"📖 {title}\n{message}\n")


def get_random_verse():
    ch = random.randint(1, 114)
    total = CHAPTER_VERSES[ch - 1]
    verse_num = random.randint(1, total)
    page = (verse_num - 1) // 50 + 1
    offset = (verse_num - 1) % 50
    url = f"{API_BASE}/chapters/{ch}/verses?{urlencode({'translations': TRANSLATION_ID_RU, 'per_page': 50, 'page': page})}"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.load(resp)
    verses = data.get("verses") or []
    if not verses or offset >= len(verses):
        return "1:1", "Во имя Аллаха, Милостивого, Милосердного."
    v = verses[offset]
    key = v.get("verse_key", f"{ch}:{verse_num}")
    trans = v.get("translations") or []
    text = (trans[0].get("text") or "").strip() if trans else v.get("text_madani", "") or "(нет перевода)"
    return key, text


def _download_mp3(verse_key: str):
    try:
        a, b = verse_key.split(":")
        ch, v = int(a), int(b)
    except (ValueError, TypeError):
        return None
    fname = f"{ch:03d}{v:03d}.mp3"
    headers = {"User-Agent": UA}
    for base in (EVERYAYAH_BASE, "http://everyayah.com/data"):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(f"{base}/{RECITER}/{fname}", headers=headers),
                timeout=30,
            ) as resp:
                want = resp.headers.get("Content-Length")
                data = resp.read(int(want)) if want else resp.read()
                if len(data) >= 15000:
                    return data
        except Exception:
            continue
    return None


def _play_file(path: str) -> bool:
    env = os.environ.copy()
    if IS_MAC:
        try:
            r = subprocess.run(
                ["afplay", path],
                timeout=90,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return r.returncode == 0
        except Exception:
            return False

    mpv = shutil.which("mpv")
    if mpv:
        try:
            r = subprocess.run(
                [mpv, "--no-video", "--no-terminal", "--really-quiet", "--ao=pulse", path],
                timeout=90,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if r.returncode == 0:
                return True
        except Exception:
            pass

    ffplay = shutil.which("ffplay")
    if ffplay:
        try:
            r = subprocess.run(
                [ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet", path],
                timeout=90,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if r.returncode == 0:
                return True
        except Exception:
            pass

    ffmpeg, paplay = shutil.which("ffmpeg"), shutil.which("paplay")
    if ffmpeg and paplay:
        try:
            pipe = (
                f"{ffmpeg} -nostdin -i {shlex.quote(path)} -f s16le -ar 44100 -ac 1 - 2>/dev/null | "
                f"{paplay} --raw --format=s16le --rate=44100 --channels=1 2>/dev/null"
            )
            r = subprocess.run(
                ["sh", "-c", pipe],
                timeout=90,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if r.returncode == 0:
                return True
        except Exception:
            pass
    return False


def play_verse_audio(verse_key: str) -> None:
    def run() -> None:
        data = _download_mp3(verse_key)
        if not data:
            return
        fd, path = tempfile.mkstemp(suffix=".mp3")
        try:
            os.write(fd, data)
            os.close(fd)
            _play_file(path)
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass

    threading.Thread(target=run, daemon=True).start()


def do_reminder() -> None:
    global _last_activate_time
    now = time.monotonic()
    if now - _last_activate_time < DEBOUNCE_SEC:
        return
    if not _notify_lock.acquire(blocking=False):
        return
    _last_activate_time = now
    try:
        ref, text = get_random_verse()
        show_notification(f"Аят из Корана ({ref})", text)
        play_verse_audio(ref)
    except Exception as e:
        show_notification("Ошибка", str(e))
    finally:
        _notify_lock.release()


def _schedule_hourly() -> None:
    global _hourly_timer
    _hourly_timer = threading.Timer(REMINDER_INTERVAL_SEC, _on_hourly)
    _hourly_timer.daemon = True
    _hourly_timer.start()


def _on_hourly() -> None:
    do_reminder()
    _schedule_hourly()


def on_hotkey() -> None:
    do_reminder()


if __name__ == "__main__":
    hotkey = "<cmd>+o" if IS_MAC else "<ctrl>+o"
    print("🕌 Quran Reminder запущен.")
    print(f"   Горячая клавиша: {hotkey}  |  Напоминание: каждый час  |  Выход: Ctrl+C\n")
    _schedule_hourly()
    with keyboard.GlobalHotKeys({hotkey: on_hotkey}) as h:
        h.join()
