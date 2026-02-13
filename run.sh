#!/bin/sh
# Запуск Quran Reminder (Linux и macOS)
cd "$(dirname "$0")"
# Linux: переменные сессии для уведомлений и звука
if [ -d "/run/user/$(id -u)" ]; then
    [ -z "$XDG_RUNTIME_DIR" ] && export XDG_RUNTIME_DIR="/run/user/$(id -u)"
    [ -z "$DBUS_SESSION_BUS_ADDRESS" ] && [ -S "/run/user/$(id -u)/bus" ] && \
        export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
    [ -z "$DISPLAY" ] && export DISPLAY=:0
fi
if [ -f ".venv/bin/python" ]; then
    exec .venv/bin/python quran_reminder.py
fi
exec python3 quran_reminder.py
