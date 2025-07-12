import os
import json
import asyncio
import pytz  # ✅ Required for timezone fix

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    Defaults,
    filters,
)

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # ✅ Add this

DATA_FILE = "user_data.json"
user_states = {}

BOT_TOKEN = os.environ["BOT_TOKEN"]

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I'm your forwarding bot.\n"
        "1. Add me to two groups as admin.\n"
        "2. Send /addsource in private chat to select the source group.\n"
        "3. Then send /adddestination to select destination group.\n"
        "Then I will forward messages accordingly."
    )

async def add_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_states[user_id] = {"step": "waiting_source"}
    await update.message.reply_text("Now send a message in the source group.")

async def add_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_states[user_id] = {"step": "waiting_destination"}
    await update.message.reply_text(
        "✅ Now send any message in the *destination* group (where I am admin).",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type

    data = load_data()

    if user_id in user_states:
        step = user_states[user_id]["step"]
        if step == "waiting_source":
            data.setdefault(user_id, {})["source"] = chat_id
            save_data(data)
            await update.message.reply_text(
                f"📥 Source group set! Chat ID: `{chat_id}`",
                parse_mode="Markdown"
            )
            user_states.pop(user_id)
            return
        elif step == "waiting_destination":
            data.setdefault(user_id, {})["destination"] = chat_id
            save_data(data)
            await update.message.reply_text(
                f"📤 Destination group set! Chat ID: `{chat_id}`",
                parse_mode="Markdown"
            )
            user_states.pop(user_id)
            return

    if chat_type in ["group", "supergroup"]:
        for uid, setting in data.items():
            if setting.get("source") == chat_id and "destination" in setting:
                try:
                    await context.bot.forward_message(
                        chat_id=setting["destination"],
                        from_chat_id=chat_id,
                        message_id=update.message.message_id
                    )
                except Exception as e:
                    print(f"[ERROR] Forwarding failed for user {uid}: {e}")

async def main():
    scheduler = AsyncIOScheduler(timezone=pytz.utc)  # ✅ This fixes the timezone error
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .scheduler(scheduler)  # ✅ Pass the custom scheduler here
        .defaults(Defaults(tzinfo=pytz.utc))  # Optional, also applies to messages
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addsource", add_source))
    application.add_handler(CommandHandler("adddestination", add_destination))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    print("[INFO] Bot is starting...")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
