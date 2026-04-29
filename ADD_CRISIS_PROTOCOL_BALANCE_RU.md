# Как добавить квест Crisis Protocol: Balance

Код запуска квеста в Telegram:

```text
BALANCE2026
```

## Что скопировать в рабочую папку бота

Скопируйте из этого архива в вашу рабочую папку проекта:

```text
quests/crisis_protocol_balance.json
assets/crisis_protocol_balance_cover.png
quest_catalog.json
```

Рабочая папка — та, где у вас лежат:

```text
bot.py
webhook_bot.py
requirements.txt
quest_catalog.json
quests/
assets/
```

Обычно это:

```text
C:\Users\mmiva\Downloads\fa_quest_lab_bot_multiquest_with_cover\fa_quest_lab_bot
```

## Проверка в PowerShell

```powershell
dir quests\crisis_protocol_balance.json
dir assets\crisis_protocol_balance_cover.png
Select-String -Path quest_catalog.json -Pattern "BALANCE2026"
```

## Отправка в GitHub

```powershell
git add .
git commit -m "Add Crisis Protocol Balance quest"
git push
```

## Render

После push нажмите:

```text
Manual Deploy → Deploy latest commit
```

Дождитесь статуса Live.

## Проверка в Telegram

```text
/reset
/start
BALANCE2026
START
I AGREE
mortgage
```

Если после `mortgage` бот открыл следующий этап, интеграция прошла успешно.
