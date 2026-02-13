#!/bin/sh
# Установка Quran Reminder (любой дистрибутив Linux и macOS)
set -e
cd "$(dirname "$0")"
echo "🕌 Установка Quran Reminder..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "Нужен Python 3. Установите: python3"
    exit 1
fi
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install -q --upgrade pip
"$VENV_DIR/bin/pip" install -q -r requirements.txt
echo ""
echo "✅ Готово. Запуск: ./run.sh (Linux) или ./run.sh (macOS)"
echo "   Linux: уведомления — libnotify; озвучка — mpv или ffmpeg."
echo "   macOS: уведомления и afplay встроены."
echo "   Автозапуск при входе: см. README.md"
