import logging
import os
import uuid
from telegram import (
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    InlineQueryHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from ai_engine import get_ai_response
from wiki_engine import get_wiki_summary
from news_engine import get_news, is_news_query

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8466855802:AAEvmgoVf7D-AVa9h_x4gpL8P6Cakhgzzzk")

# In-memory user mode store
user_modes: dict[int, str] = {}

MODES = {
    "smart": {"label": "🧠 Smart Mode", "desc": "Intelligent, detailed responses", "emoji": "🧠"},
    "funny": {"label": "😂 Funny Mode", "desc": "Humorous, witty responses", "emoji": "😂"},
    "savage": {"label": "🔥 Savage Mode", "desc": "Brutally honest responses", "emoji": "🔥"},
}


def get_user_mode(user_id: int) -> str:
    return user_modes.get(user_id, "smart")


def mode_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    buttons = []
    for key, val in MODES.items():
        label = f"✅ {val['label']}" if key == current_mode else val["label"]
        buttons.append([InlineKeyboardButton(label, callback_data=f"mode_{key}")])
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    mode = get_user_mode(user.id)
    text = (
        f"👋 Hey {user.first_name}! I'm your AI-powered inline bot.\n\n"
        f"🤖 *How to use me:*\n"
        f"• Type `@{context.bot.username} your question` anywhere\n"
        f"• I'll reply with AI-powered answers + latest news!\n\n"
        f"⚙️ *Commands:*\n"
        f"/mode — Switch personality mode\n"
        f"/help — Show help\n\n"
        f"🎭 *Current Mode:* {MODES[mode]['label']}\n\n"
        f"🧠 *Powered by:* SambaNova (Llama 3.3 70B) + Gemini"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Bot Help*\n\n"
        "🔹 *Inline Usage:*\n"
        f"Type `@botusername <your query>` in any chat.\n\n"
        "🔹 *Commands:*\n"
        "/start — Welcome message\n"
        "/mode — Change personality mode\n"
        "/help — This message\n\n"
        "🎭 *Personality Modes:*\n"
        "🧠 Smart — Detailed, informative answers\n"
        "😂 Funny — Humorous & witty replies\n"
        "🔥 Savage — Brutally honest responses\n\n"
        "📰 *News Feature:*\n"
        "Ask about news, current events, sports scores — bot fetches real-time news!\n\n"
        "🧠 *Powered by:* SambaNova Llama 3.3 70B + Google Gemini\n"
        "📚 *Enhanced by:* Wikipedia + NewsAPI"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current = get_user_mode(user_id)
    text = (
        f"🎭 *Select Personality Mode*\n\n"
        f"Current: {MODES[current]['label']}\n\n"
        f"Choose a mode below:"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=mode_keyboard(current)
    )


async def mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("mode_"):
        new_mode = data.replace("mode_", "")
        if new_mode in MODES:
            user_modes[user_id] = new_mode
            text = (
                f"✅ *Mode switched to {MODES[new_mode]['label']}*\n\n"
                f"{MODES[new_mode]['emoji']} {MODES[new_mode]['desc']}\n\n"
                f"Now use me inline: `@{context.bot.username} your question`"
            )
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=mode_keyboard(new_mode),
            )


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    user_id = update.inline_query.from_user.id
    mode = get_user_mode(user_id)

    if not query:
        results = [
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="💬 Ask me anything!",
                description="Type your question after @botname",
                input_message_content=InputTextMessageContent(
                    "Type your question after @botname to get an AI response! 🤖"
                ),
            )
        ]
        await update.inline_query.answer(results, cache_time=0)
        return

    try:
        mode_badge = MODES[mode]["emoji"]

        # Fetch wiki + news in parallel context
        wiki_info = await get_wiki_summary(query)
        news_info = await get_news(query) if is_news_query(query) else None

        # Get AI response
        ai_response = await get_ai_response(
            query, mode, wiki_context=wiki_info, news_context=news_info
        )

        # Format reply
        response_text = f"{mode_badge} *AI Response* ({MODES[mode]['label']})\n\n"
        response_text += f"❓ *Q:* {query}\n\n"
        response_text += f"💬 *A:* {ai_response}"

        if news_info:
            response_text += f"\n\n📰 *Latest News:*\n{news_info}"
        elif wiki_info:
            response_text += f"\n\n📚 *Wikipedia:*\n_{wiki_info[:250]}..._"

        results = [
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=f"{mode_badge} {query[:50]}",
                description=ai_response[:100] + "...",
                input_message_content=InputTextMessageContent(
                    response_text,
                    parse_mode="Markdown",
                ),
            )
        ]
    except Exception as e:
        logger.error(f"Inline query error: {e}")
        results = [
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="⚠️ Error occurred",
                description="Something went wrong. Try again!",
                input_message_content=InputTextMessageContent(
                    "⚠️ Sorry, something went wrong. Please try again later."
                ),
            )
        ]

    await update.inline_query.answer(results, cache_time=0)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("mode", mode_cmd))
    app.add_handler(CallbackQueryHandler(mode_callback, pattern="^mode_"))
    app.add_handler(InlineQueryHandler(inline_query))
    logger.info("🤖 Bot is running — SambaNova + Gemini + NewsAPI!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
