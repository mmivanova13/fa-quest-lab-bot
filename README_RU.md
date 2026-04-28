# FA Quest Lab Bot

Это версия бота с поддержкой нескольких квестов по кодам.

Один Telegram-бот может запускать разные сценарии. Студенты получают код от преподавателя, вводят его в бота, и бот открывает нужный квест.

## Что уже добавлено

В `quest_catalog.json` есть два рабочих кода для одного и того же квеста:

```text
MISSING2026
MR2026FA
```

Оба запускают квест:

```text
The Missing Reel
```

Финальная фраза квеста:

```text
KEEP THE CITY REAL BEFORE THE FEED MAKES IT FLAT.
```

## Структура проекта

```text
fa_quest_lab_bot/
  bot.py
  quest_catalog.json
  requirements.txt
  .env.example
  quests/
    missing_reel.json
    template_quest.json
  teacher_notes.md
  bot_flow_table.csv
```

## Как запустить

### 1. Создайте Telegram-бота

В Telegram откройте `@BotFather`, отправьте команду:

```text
/newbot
```

BotFather попросит название и username, затем выдаст токен.

### 2. Подготовьте проект

Откройте терминал в папке проекта и выполните:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Затем установите зависимости:

```bash
pip install -r requirements.txt
```

### 3. Добавьте токен

Скопируйте файл `.env.example` в `.env`.

Windows PowerShell:

```powershell
copy .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

Откройте `.env` и вставьте токен:

```text
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
```

### 4. Запустите бота

```bash
python bot.py
```

После запуска откройте вашего бота в Telegram и отправьте:

```text
/start
```

Бот попросит код квеста. Введите:

```text
MISSING2026
```

или:

```text
MR2026FA
```

## Как добавить новый квест

### 1. Создайте новый JSON-файл

Скопируйте шаблон:

```text
quests/template_quest.json
```

Например:

```text
quests/finance_city.json
```

Заполните поля:

- `bot_title`
- `final_phrase`
- `start_message`
- `safety_message`
- `finish_message`
- `locations`

У каждой локации должны быть поля:

```text
id
title
location_name
address
coordinates
map_link
expected_answer
accepted_answers
skip_code
fragment
message
question
hints
wrong_reply
success_reply
speaking_task
next_directions
```

### 2. Добавьте код в `quest_catalog.json`

Пример:

```json
{
  "quests": {
    "FINCITY01": {
      "title": "Finance City Quest",
      "file": "quests/finance_city.json",
      "active": true,
      "description": "A finance-themed city quest."
    }
  }
}
```

Важно: не удаляйте уже существующие коды, если они нужны.

### 3. Перезапустите бота

После изменения `quest_catalog.json` или JSON-файлов квестов остановите бота и запустите заново:

```bash
python bot.py
```

## Как сделать разные коды для разных групп

Можно создать несколько кодов, которые ведут к одному файлу:

```json
{
  "MR-GROUP1": {
    "title": "The Missing Reel",
    "file": "quests/missing_reel.json",
    "active": true,
    "description": "Group 1."
  },
  "MR-GROUP2": {
    "title": "The Missing Reel",
    "file": "quests/missing_reel.json",
    "active": true,
    "description": "Group 2."
  }
}
```

Коды нечувствительны к регистру, пробелам, дефисам и подчёркиваниям. Например, бот поймёт как один и тот же код:

```text
MR2026FA
mr2026fa
MR-2026-FA
MR 2026 FA
```

## Команды бота

```text
/start — ввести код и начать
/start CODE — сразу начать по коду
/code — сменить код квеста
/reset — сбросить текущий квест
/hint — получить подсказку
/whereami — показать текущую точку
/progress — показать прогресс
/quest — показать текущий квест
/quests — показать названия доступных квестов без кодов
/help — справка
```

Студенты также могут писать текстом:

```text
HINT
WHERE AM I?
ARRIVED
RESET
CHANGE QUEST
```

## Аварийные коды преподавателя

В каждом квесте у локации есть поле `skip_code`.

Например:

```json
"skip_code": "SKIP3"
```

Если точка недоступна, табличка закрыта или команда застряла, преподаватель может дать код `SKIP3`, и бот засчитает локацию как пройденную.

## Важно перед занятием

1. Пройдите маршрут лично.
2. Проверьте, что все ответы видны на месте.
3. Проверьте карты и точки остановки.
4. Проверьте, что бот запускается.
5. Проведите тест в отдельном Telegram-чате.
6. Убедитесь, что у каждой команды есть правильный код.


## Обложка квеста

После ввода правильного кода бот автоматически отправляет изображение-обложку, если оно указано в `quest_catalog.json`.

Для The Missing Reel обложка лежит здесь:

```text
assets/missing_reel_cover.png
```

В каталоге это выглядит так:

```json
"cover_image": "assets/missing_reel_cover.png",
"cover_caption": "Quest unlocked: The Missing Reel\n\nThe city kept the backup.\nNow find it."
```

Чтобы добавить обложку к новому квесту, положите файл в папку `assets/` и добавьте путь в соответствующий блок кода в `quest_catalog.json`.

---

# Webhook-версия для бесплатного web-хостинга

Эта версия проекта умеет работать не только через polling (`bot.py`), но и через webhook (`webhook_bot.py`). Webhook лучше подходит для бесплатных web-hosting платформ, потому что хостинг видит обычное веб-приложение с HTTP endpoint.

## Какие файлы важны

```text
webhook_bot.py      — webhook entry point
Dockerfile          — сборка контейнера для хостинга
requirements.txt    — зависимости, включая FastAPI и Uvicorn
bot.py              — основная логика квеста, используется webhook_bot.py
```

## Переменные окружения на хостинге

Добавьте в настройках хостинга:

```text
TELEGRAM_BOT_TOKEN = ваш токен от BotFather
WEBHOOK_URL = публичный URL вашего приложения, например https://your-app.example.com
```

Опционально:

```text
WEBHOOK_PATH = /telegram-webhook
WEBHOOK_SECRET_TOKEN = любая длинная случайная строка
```

`WEBHOOK_URL` должен быть именно публичным адресом приложения без слэша в конце. Пример:

```text
https://fa-quest-lab-bot.example.com
```

Бот сам поставит webhook Telegram на адрес:

```text
https://fa-quest-lab-bot.example.com/telegram-webhook
```

## Команда запуска без Docker

Если платформа не использует Dockerfile, укажите Start Command:

```bash
uvicorn webhook_bot:web_app --host 0.0.0.0 --port $PORT
```

Если `$PORT` не поддерживается, используйте порт, который требует ваша платформа.

## Команда установки зависимостей

```bash
pip install -r requirements.txt
```

## Проверка

После запуска откройте в браузере публичный URL приложения. Должен появиться JSON примерно такого вида:

```json
{"status":"ok","bot":"FA Quest Lab","mode":"webhook"}
```

Потом откройте Telegram и отправьте боту `/start`.

## Важно

Не запускайте одновременно polling-версию (`python bot.py`) и webhook-версию на хостинге. У одного Telegram-бота должен быть один активный способ получения обновлений.
