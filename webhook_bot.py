"""Webhook entry point for FA Quest Lab Telegram bot.

Use this file on free web-hosting platforms that expect an HTTP web service.
It exposes:
- GET /            health check
- GET /health      health check
- POST /telegram-webhook   Telegram webhook endpoint

Required environment variables:
- TELEGRAM_BOT_TOKEN
- WEBHOOK_URL, for example https://your-app-name.example.com

Optional:
- WEBHOOK_PATH, default /telegram-webhook
- WEBHOOK_SECRET_TOKEN, any long random string; if set, Telegram requests must include it.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from telegram import Update

from bot import BASE_DIR, build_app

load_dotenv(BASE_DIR / ".env")

WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/telegram-webhook")
if not WEBHOOK_PATH.startswith("/"):
    WEBHOOK_PATH = "/" + WEBHOOK_PATH

WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN")

telegram_app = build_app()
web_app = FastAPI(title="FA Quest Lab Bot")


def get_public_webhook_url() -> str:
    """Build the public Telegram webhook URL from environment variables."""
    public_base = (
        os.getenv("WEBHOOK_URL")
        or os.getenv("RENDER_EXTERNAL_URL")
        or (f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN')}" if os.getenv("RAILWAY_PUBLIC_DOMAIN") else None)
        or (f"https://{os.getenv('KOYEB_PUBLIC_DOMAIN')}" if os.getenv("KOYEB_PUBLIC_DOMAIN") else None)
    )
    if not public_base:
        raise RuntimeError(
            "WEBHOOK_URL is not set. Add your public app URL, for example: "
            "WEBHOOK_URL=https://your-app-domain"
        )
    return public_base.rstrip("/") + WEBHOOK_PATH


@web_app.on_event("startup")
async def on_startup() -> None:
    await telegram_app.initialize()
    await telegram_app.start()

    webhook_url = get_public_webhook_url()
    await telegram_app.bot.set_webhook(
        url=webhook_url,
        allowed_updates=Update.ALL_TYPES,
        secret_token=WEBHOOK_SECRET_TOKEN,
    )
    print(f"FA Quest Lab webhook bot is running at {webhook_url}")


@web_app.on_event("shutdown")
async def on_shutdown() -> None:
    await telegram_app.stop()
    await telegram_app.shutdown()


@web_app.get("/")
async def root() -> Dict[str, str]:
    return {
        "status": "ok",
        "bot": "FA Quest Lab",
        "mode": "webhook",
        "webhook_path": WEBHOOK_PATH,
    }


@web_app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@web_app.post(WEBHOOK_PATH)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> Dict[str, bool]:
    if WEBHOOK_SECRET_TOKEN and x_telegram_bot_api_secret_token != WEBHOOK_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid Telegram secret token")

    payload: Dict[str, Any] = await request.json()
    update = Update.de_json(payload, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}
