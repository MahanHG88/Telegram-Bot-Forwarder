import os
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

DATA_FILE = "user_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

user_states = {}

BOT_TOKEN = os.environ["BOT_TOKEN"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[DEBUG] /start from user {update.effective_user.id}")
    await update.message.reply_text(
        "👋 Hi! I'm your forwarding bot.\n"
        "1. Add me to two groups as admin.\n"
        "2. Send /addsource in private chat to select the source group.\n"
        "3. Then send /adddestination to select destination group.\n"
        "Then I will forward messages accordingly."
    )

async def add_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    print(f"[DEBUG] /addsource called by user {user_id}")
    user_states[user_id] = {"step": "waiting_source"}
    await update.message.reply_text("Now send a message in the source group.")
    

async def add_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    print(f"[DEBUG] /adddestination called by user {user_id}")
    user_states[user_id] = {"step": "waiting_destination"}
    await update.message.reply_text(
        "✅ Now send any message in the *destination* group (where I am admin)."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type

    # Debug prints
    print(f"[DEBUG] Message from user {user_id} in chat {chat_id} ({chat_type})")

    data = load_data()

    if user_id in user_states:
        step = user_states[user_id]["step"]
        if step == "waiting_source":
            if user_id not in data:
                data[user_id] = {}
            data[user_id]["source"] = chat_id
            save_data(data)
            await update.message.reply_text(
                f"📥 Source group set! Chat ID: `{chat_id}`", parse_mode="Markdown"
            )
            print(f"[DEBUG] User {user_id} set source to {chat_id}")
            user_states.pop(user_id)
            return
        elif step == "waiting_destination":
            if user_id not in data:
                data[user_id] = {}
            data[user_id]["destination"] = chat_id
            save_data(data)
            await update.message.reply_text(
                f"📤 Destination group set! Chat ID: `{chat_id}`", parse_mode="Markdown"
            )
            print(f"[DEBUG] User {user_id} set destination to {chat_id}")
            user_states.pop(user_id)
            return

    # Forward messages if chat is a group and matches any user's source
    if chat_type in ["group", "supergroup"]:
        for uid, setting in data.items():
            if "source" in setting and "destination" in setting:
                if setting["source"] == chat_id:
                    try:
                        print(f"[DEBUG] Forwarding message from {chat_id} to {setting['destination']} for user {uid}")
                        await context.bot.forward_message(
                            chat_id=setting["destination"],
                            from_chat_id=chat_id,
                            message_id=update.message.message_id,
                        )
                    except Exception as e:
                        print(f"[ERROR] Forwarding failed for user {uid}: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addsource", add_source))
    app.add_handler(CommandHandler("adddestination", add_destination))
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_message))

    print("[INFO] Bot is starting...")
    app.run_polling()