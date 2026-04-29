# Add The Lost Coordinate to FA Quest Lab

This package adds a second/next quest to the existing webhook Telegram bot.

## Quest code

COORDINATE2026

## Files to copy into your working bot folder

Copy these files/folders into your existing working folder:

- quests/lost_coordinate.json
- assets/lost_coordinate_cover.png
- quest_catalog.json

Your working folder is the folder that contains:
bot.py, webhook_bot.py, requirements.txt, quest_catalog.json, quests/, assets/

## Then upload to GitHub

Open PowerShell in your working folder and run:

git add .
git commit -m "Add The Lost Coordinate quest"
git push

## Then redeploy on Render

Render dashboard → your service → Manual Deploy → Deploy latest commit.

## Test in Telegram

/start
COORDINATE2026
START
I AGREE

First answer:
departure
