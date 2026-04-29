"""Multi-quest Telegram bot for FA Quest Lab.

One Telegram bot can run many walking quests.
Students unlock a quest by entering a teacher-provided code, for example:
- MISSING2026
- MR2026FA

Project structure:
- quest_catalog.json stores quest codes and file paths.
- quests/*.json stores individual quest scripts.
- bot_state.pickle stores chat progress between restarts.

Tested for the python-telegram-bot v22.x async API pattern.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PicklePersistence,
    filters,
)

BASE_DIR = Path(__file__).resolve().parent
CATALOG_FILE = BASE_DIR / "quest_catalog.json"
PERSISTENCE_FILE = BASE_DIR / "bot_state.pickle"

WAITING_CODE = "waiting_code"
INTRO = "intro"
SAFETY = "safety"
ANSWERING = "answering"
BETWEEN = "between"
FINISHED = "finished"
FINAL_CHOICE = "final_choice"

_QUEST_CACHE: Dict[str, Dict[str, Any]] = {}


def load_catalog() -> Dict[str, Any]:
    with CATALOG_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


CATALOG = load_catalog()


def normalize(text: str) -> str:
    """Normalize user input for forgiving matching."""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.lower().strip()
    text = text.replace("ё", "е")
    text = text.replace("’", "'").replace("`", "'")
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    text = re.sub(r"[^\w\s\-а-яА-Я]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_code(text: str) -> str:
    """Normalize quest codes: remove spaces/hyphens and compare uppercase."""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.upper().strip()
    text = text.replace(" ", "").replace("-", "").replace("_", "")
    text = re.sub(r"[^A-Z0-9]", "", text)
    return text


def catalog_code_lookup(raw_code: str) -> Optional[str]:
    """Return the real catalog key for a user-entered code."""
    wanted = normalize_code(raw_code)
    for code in CATALOG.get("quests", {}):
        if normalize_code(code) == wanted:
            return code
    return None


def load_quest_for_code(code: str) -> Dict[str, Any]:
    """Load quest JSON by catalog code."""
    if code in _QUEST_CACHE:
        return _QUEST_CACHE[code]

    entry = CATALOG["quests"][code]
    quest_path = BASE_DIR / entry["file"]
    with quest_path.open("r", encoding="utf-8") as f:
        quest = json.load(f)

    quest["_catalog_code"] = code
    quest["_catalog_title"] = entry.get("title", quest.get("bot_title", code))
    _QUEST_CACHE[code] = quest
    return quest



async def send_quest_cover_if_available(update: Update, entry: Dict[str, Any], title: str) -> None:
    """Send a quest cover image after a valid code, if cover_image is configured."""
    cover_image = entry.get("cover_image")
    if not cover_image:
        return

    image_path = BASE_DIR / cover_image
    if not image_path.exists():
        await update.effective_message.reply_text(
            f"Quest unlocked: {title}\n\n"
            "Cover image is configured, but the image file was not found. "
            "The quest will continue without the cover."
        )
        return

    caption = entry.get("cover_caption") or f"Quest unlocked: {title}"
    with image_path.open("rb") as photo:
        await update.effective_message.reply_photo(photo=photo, caption=caption)


def get_selected_code(chat_data: Dict[str, Any]) -> Optional[str]:
    return chat_data.get("quest_code")


def get_current_quest(chat_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    code = get_selected_code(chat_data)
    if not code:
        return None
    return load_quest_for_code(code)


def get_locations(chat_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    quest = get_current_quest(chat_data)
    return quest.get("locations", []) if quest else []


def set_waiting_for_code(chat_data: Dict[str, Any]) -> None:
    chat_data.pop("quest_code", None)
    chat_data["progress"] = {
        "phase": WAITING_CODE,
        "location_index": 0,
        "hints_used": 0,
        "fragments": [],
        "completed": [],
    }


def init_quest_progress(chat_data: Dict[str, Any], code: str) -> Dict[str, Any]:
    chat_data["quest_code"] = code
    chat_data["progress"] = {
        "phase": INTRO,
        "location_index": 0,
        "hints_used": 0,
        "fragments": [],
        "completed": [],
    }
    return chat_data["progress"]


def get_progress(chat_data: Dict[str, Any]) -> Dict[str, Any]:
    if "progress" not in chat_data:
        set_waiting_for_code(chat_data)
    return chat_data["progress"]


def reset_current_quest(chat_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    code = get_selected_code(chat_data)
    if not code:
        set_waiting_for_code(chat_data)
        return None
    return init_quest_progress(chat_data, code)


def code_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def command_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["HINT", "WHERE AM I?"], ["CHANGE QUEST", "RESET"]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def between_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["ARRIVED"], ["WHERE AM I?", "CHANGE QUEST"], ["RESET"]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def intro_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["START"], ["CHANGE QUEST"]], resize_keyboard=True, one_time_keyboard=True)


def safety_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["I AGREE"], ["CHANGE QUEST"]], resize_keyboard=True, one_time_keyboard=True)


def format_destination_intro(location: Dict[str, Any]) -> str:
    parts = ["NEXT DESTINATION"]

    title = location.get("title", "")
    location_name = location.get("location_name", "")
    address = location.get("address", "")
    map_link = location.get("map_link", "")
    next_directions = location.get("next_directions", "")

    if title:
        parts.append(title)

    if location_name:
        parts.append("\U0001F4CD Location: " + location_name)

    if address:
        parts.append("\U0001F4CC Address / point: " + address)

    if map_link:
        parts.append("\U0001F5FA\ufe0f Yandex Maps:")
        parts.append(map_link)

    if next_directions:
        parts.append("Route note:")
        parts.append(next_directions)

    parts.append("When your team arrives at the point, press ARRIVED or type ARRIVED.")

    return "\n\n".join(parts)


def format_location_task(location: Dict[str, Any]) -> str:
    parts = []

    title = location.get("title", "")
    location_name = location.get("location_name", "")
    message = location.get("message", "")
    question = location.get("question", "")

    if title:
        parts.append(title)

    if location_name:
        parts.append(location_name)

    if message:
        parts.append(message)

    if question:
        parts.append("\u2753")
        parts.append(question)

    parts.append("Type your answer, or type HINT if you need help.")

    return "\n\n".join(parts)




def final_profile_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["SHARE", "SELL"], ["DESTROY", "HIDE"]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def retry_code_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["RESET"]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


async def ask_for_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    set_waiting_for_code(context.chat_data)
    await update.effective_message.reply_text(CATALOG["welcome_message"], reply_markup=code_keyboard())


async def unlock_quest_by_code(update: Update, context: ContextTypes.DEFAULT_TYPE, raw_code: str) -> bool:
    message = update.effective_message
    code = catalog_code_lookup(raw_code)

    if not code:
        set_waiting_for_code(context.chat_data)
        await message.reply_text(
            CATALOG.get("invalid_code_message", "Unknown quest code. Try again."),
            reply_markup=retry_code_keyboard(),
        )
        return False

    entry = CATALOG["quests"][code]
    if not entry.get("active", False):
        set_waiting_for_code(context.chat_data)
        await message.reply_text(
            CATALOG.get("inactive_code_message", "This quest is not active right now."),
            reply_markup=retry_code_keyboard(),
        )
        return False

    try:
        quest = load_quest_for_code(code)
    except FileNotFoundError:
        set_waiting_for_code(context.chat_data)
        await message.reply_text(
            "This quest code exists, but its JSON file was not found.\n\n"
            "Ask the teacher to check quest_catalog.json.",
            reply_markup=retry_code_keyboard(),
        )
        return False
    except json.JSONDecodeError as exc:
        await message.reply_text(
            "This quest code exists, but its JSON file has a formatting error.\n\n"
            f"Technical detail: {exc}"
        )
        return False

    init_quest_progress(context.chat_data, code)
    title = entry.get("title", quest.get("bot_title", code))

    await send_quest_cover_if_available(update, entry, title)

    await message.reply_text(
        f"Code: {code}\n\n"
        f"{quest['start_message']}",
        reply_markup=intro_keyboard(),
    )
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        await unlock_quest_by_code(update, context, " ".join(context.args))
        return
    await ask_for_code(update, context)


async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        await unlock_quest_by_code(update, context, " ".join(context.args))
        return
    await ask_for_code(update, context)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    quest = get_current_quest(context.chat_data)
    if not quest:
        await ask_for_code(update, context)
        return

    reset_current_quest(context.chat_data)
    code = get_selected_code(context.chat_data)
    title = quest.get("_catalog_title", quest.get("bot_title", code))
    await update.effective_message.reply_text(
        f"Progress reset for: {title}\n"
        f"Code: {code}\n\n"
        f"{quest['start_message']}",
        reply_markup=intro_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Commands:\n"
        "/start — enter a quest code and begin\n"
        "/start CODE — begin with a specific quest code\n"
        "/code — change quest code\n"
        "/reset — reset the current quest\n"
        "/hint — get the next hint for the current frame\n"
        "/whereami — show your current frame and directions\n"
        "/progress — show unlocked fragments\n"
        "/quest — show current quest\n"
        "Cover images are sent automatically after a valid quest code.\n\n"
        "You can also type HINT, WHERE AM I?, RESET, CHANGE QUEST or ARRIVED."
    )


async def quest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    code = get_selected_code(context.chat_data)
    quest = get_current_quest(context.chat_data)
    if not code or not quest:
        await update.effective_message.reply_text("No quest selected yet. Use /code and enter your teacher’s code.")
        return

    entry = CATALOG["quests"][code]
    await update.effective_message.reply_text(
        f"Current quest: {entry.get('title', quest.get('bot_title', code))}\n"
        f"Code: {code}\n"
        f"Final phrase: {quest.get('final_phrase', 'not set')}"
    )


async def quests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    active_titles = [
        entry.get("title", code)
        for code, entry in CATALOG.get("quests", {}).items()
        if entry.get("active", False)
    ]
    unique_titles = []
    for title in active_titles:
        if title not in unique_titles:
            unique_titles.append(title)

    text = "Available quest titles:\n" + "\n".join(f"• {title}" for title in unique_titles)
    text += "\n\nQuest codes are provided by your teacher."
    await update.effective_message.reply_text(text)


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    progress = get_progress(context.chat_data)
    quest = get_current_quest(context.chat_data)
    if not quest:
        await update.effective_message.reply_text("No quest selected yet. Enter your quest code first.")
        return

    fragments = " ".join(progress.get("fragments", [])) or "none yet"
    completed = ", ".join(progress.get("completed", [])) or "none yet"
    await update.effective_message.reply_text(
        f"Quest: {quest.get('_catalog_title', quest.get('bot_title'))}\n"
        f"Phase: {progress.get('phase')}\n"
        f"Completed frames: {completed}\n"
        f"Unlocked fragments: {fragments}"
    )



async def send_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    progress = get_progress(context.chat_data)
    quest = get_current_quest(context.chat_data)

    if not quest:
        await ask_for_code(update, context)
        return

    final_profiles = quest.get("final_profiles", {})

    if final_profiles:
        progress["phase"] = FINAL_CHOICE
        await update.effective_message.reply_text(
            quest.get("final_choice_message", "Choose your final profile."),
            reply_markup=final_profile_keyboard(),
        )
        return

    progress["phase"] = FINISHED
    await update.effective_message.reply_text(
        quest.get("finish_message", "The quest is complete."),
        reply_markup=ReplyKeyboardRemove(),
    )


async def send_destination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    progress = get_progress(context.chat_data)
    locations = get_locations(context.chat_data)
    quest = get_current_quest(context.chat_data)

    if not quest:
        await ask_for_code(update, context)
        return

    index = progress["location_index"]

    if index >= len(locations):
        await send_finish(update, context)
        return

    location = locations[index]
    progress["phase"] = BETWEEN
    progress["hints_used"] = 0

    await update.effective_message.reply_text(
        format_destination_intro(location),
        reply_markup=between_keyboard(),
        disable_web_page_preview=True,
    )


async def send_location_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    progress = get_progress(context.chat_data)
    locations = get_locations(context.chat_data)
    quest = get_current_quest(context.chat_data)

    if not quest:
        await ask_for_code(update, context)
        return

    index = progress["location_index"]

    if index >= len(locations):
        await send_finish(update, context)
        return

    location = locations[index]
    progress["phase"] = ANSWERING
    progress["hints_used"] = 0

    await update.effective_message.reply_text(
        format_location_task(location),
        reply_markup=command_keyboard(),
        disable_web_page_preview=True,
    )


async def whereami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    progress = get_progress(context.chat_data)
    phase = progress.get("phase", WAITING_CODE)
    index = progress.get("location_index", 0)
    quest = get_current_quest(context.chat_data)
    locations = get_locations(context.chat_data)

    if not quest:
        await update.effective_message.reply_text("No quest selected yet. Enter your quest code first.")
        return

    if phase == WAITING_CODE:
        await update.effective_message.reply_text("Enter your quest code to begin.")
        return
    if phase in {INTRO, SAFETY}:
        await update.effective_message.reply_text("You are at the beginning of the quest. Type START to begin.")
        return
    if phase == FINISHED or index >= len(locations):
        await update.effective_message.reply_text("The quest is complete. Final phrase: " + quest.get("final_phrase", ""))
        return

    location = locations[index]
    await update.effective_message.reply_text(
        f"Current frame: {location['id']} — {location['title']}\n"
        f"\U0001F4CD Location: {location['location_name']}\n"
        f"\U0001F4CC Address / point: {location['address']}\n"
        f"\U0001F5FA\ufe0f Map: {location['map_link']}\n"
        f"Phase: {phase}\n\n"
        f"Unlocked fragments: {' '.join(progress.get('fragments', [])) or 'none yet'}",
        disable_web_page_preview=True,
    )


async def hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    progress = get_progress(context.chat_data)
    locations = get_locations(context.chat_data)

    if not get_current_quest(context.chat_data):
        await update.effective_message.reply_text("No quest selected yet. Enter your quest code first.")
        return

    if progress.get("phase") != ANSWERING:
        await update.effective_message.reply_text("No active question right now. Type ARRIVED when you reach the next point.")
        return

    location = locations[progress["location_index"]]
    hints = location.get("hints", [])
    used = progress.get("hints_used", 0)

    if used < len(hints):
        progress["hints_used"] = used + 1
        await update.effective_message.reply_text(f"Hint {used + 1}: {hints[used]}")
    else:
        await update.effective_message.reply_text(
            "No more hints for this frame. Ask your teacher for help or check the place again."
        )


async def handle_correct_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, skipped: bool = False) -> None:
    progress = get_progress(context.chat_data)
    locations = get_locations(context.chat_data)
    quest = get_current_quest(context.chat_data)

    if not quest:
        await ask_for_code(update, context)
        return

    location = locations[progress["location_index"]]

    if location["fragment"] not in progress["fragments"]:
        progress["fragments"].append(location["fragment"])
    if location["id"] not in progress["completed"]:
        progress["completed"].append(location["id"])

    prefix = "Teacher override accepted.\n\n" if skipped else ""
    await update.effective_message.reply_text(prefix + location["success_reply"])

    if location.get("speaking_task"):
        await update.effective_message.reply_text("🎙 Speaking task:\n" + location["speaking_task"])

    progress["location_index"] += 1
    progress["hints_used"] = 0

    if progress["location_index"] >= len(locations):
        progress["phase"] = FINISHED
        await update.effective_message.reply_text(quest["finish_message"], reply_markup=ReplyKeyboardRemove())
        return

    await send_destination(update, context)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    text = message.text or ""
    normalized = normalize(text)
    progress = get_progress(context.chat_data)
    phase = progress.get("phase", WAITING_CODE)

    if normalized in {"reset", "RESET"}:
        await reset(update, context)
        return
    if normalized in {"change quest", "new quest", "code", "quest code", "CODE"}:
        await ask_for_code(update, context)
        return
    if normalized in {"hint", "/hint"}:
        await hint(update, context)
        return
    if normalized in {"where am i", "whereami", "/whereami"}:
        await whereami(update, context)
        return
    if normalized in {"progress", "/progress"}:
        await progress_command(update, context)
        return

    if phase == WAITING_CODE:
        await unlock_quest_by_code(update, context, text)
        return

    quest = get_current_quest(context.chat_data)
    if not quest:
        await ask_for_code(update, context)
        return

    if phase == INTRO:
        if normalized == "start":
            progress["phase"] = SAFETY
            await message.reply_text(quest["safety_message"], reply_markup=safety_keyboard())
        else:
            await message.reply_text("Type START when your team is ready.", reply_markup=intro_keyboard())
        return

    if normalized in {"code", "change quest", "change quest code"}:
        await ask_for_code(update, context)
        return

    if normalized == "reset":
        await reset_command(update, context)
        return



    if phase == SAFETY:
        if normalized in {"i agree", "agree", "yes", "ok"}:
            await send_destination(update, context)
        else:
            await message.reply_text("Please type I AGREE to continue.", reply_markup=safety_keyboard())
        return

    if phase == BETWEEN:
        if normalized in {"arrived", "next", "ready", "continue"}:
            await send_location_task(update, context)
        else:
            await message.reply_text("Type ARRIVED when your team is at the next location.", reply_markup=between_keyboard())
        return


    if phase == FINAL_CHOICE:
        quest = get_current_quest(context.chat_data)
        final_profiles = quest.get("final_profiles", {}) if quest else {}
        choice = normalized.upper()

        if choice in final_profiles:
            progress["phase"] = FINISHED
            await message.reply_text(
                final_profiles[choice],
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            await message.reply_text(
                "Choose one of the final options: SHARE, SELL, DESTROY or HIDE.",
                reply_markup=final_profile_keyboard(),
            )
        return

    if phase == FINISHED:
        await message.reply_text("The quest is already complete. Use /reset for the same quest or /code for another quest.")
        return

    if phase == ANSWERING:
        locations = get_locations(context.chat_data)
        location = locations[progress["location_index"]]
        accepted = {normalize(ans) for ans in location["accepted_answers"]}
        skip_code = normalize(location.get("skip_code", ""))

        if normalized == skip_code:
            await handle_correct_answer(update, context, skipped=True)
            return

        if normalized in accepted:
            await handle_correct_answer(update, context)
            return

        await message.reply_text(location["wrong_reply"])
        await hint(update, context)
        return

    await message.reply_text("I am not sure where we are in the quest. Use /reset to restart or /code to choose a quest.")


def build_app() -> Application:
    load_dotenv(BASE_DIR / ".env")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and paste your BotFather token."
        )

    persistence = PicklePersistence(filepath=str(PERSISTENCE_FILE))
    app = ApplicationBuilder().token(token).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("code", code_command))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("hint", hint))
    app.add_handler(CommandHandler("whereami", whereami))
    app.add_handler(CommandHandler("progress", progress_command))
    app.add_handler(CommandHandler("quest", quest_command))
    app.add_handler(CommandHandler("quests", quests_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return app


def main() -> None:
    app = build_app()
    print("FA Quest Lab bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
