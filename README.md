# Quran Reminder

Аят из Корана по горячей клавише и **автоматически раз в час** (время в спящем режиме не учитывается — напоминание не срабатывает, пока устройство спит).

- **Linux** и **macOS**
- Текст: API Quran.com (перевод на русском)
- Озвучка: рецитация с everyayah.com (Muhammad Ayyoub)

## Установка (любой дистрибутив)

```bash
cd quran
chmod +x install.sh run.sh
./install.sh
```

Зависимости: **Python 3** и **pynput** (ставятся через `install.sh`).

- **Linux:** для уведомлений желательно установить `libnotify`, для озвучки — `mpv` или `ffmpeg`.
- **macOS:** уведомления и воспроизведение (afplay) встроены.

## Запуск

```bash
./run.sh
```

- **Горячая клавиша:** Ctrl+O (Linux) или Cmd+O (macOS) — показать аят и озвучить.
- **Раз в час** показывается напоминание с новым аятом (когда компьютер не в спящем режиме).

## Автозапуск при входе в систему

**Linux:** скопируйте `Quran-Reminder.desktop` в автозапуск и укажите свой путь к папке:

```bash
mkdir -p ~/.config/autostart
sed "s|PATH_TO_QURAN|$(pwd)|g" Quran-Reminder.desktop > ~/.config/autostart/quran-reminder.desktop
```

**macOS:** добавьте «Программы входа» (Login Items): укажите приложение Terminal и команду `open -a Terminal -n --args -e "bash -c 'cd /путь/к/quran && ./run.sh'"` или создайте приложение-обёртку.

## Файлы

| Файл | Назначение |
|------|------------|
| `quran_reminder.py` | Основной скрипт |
| `install.sh` | Установка (venv + pynput) |
| `run.sh` | Запуск |
| `requirements.txt` | Зависимости Python |
| `Quran-Reminder.desktop` | Ярлык/автозапуск (Linux) |
