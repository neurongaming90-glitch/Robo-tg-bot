import asyncio
import html
import logging
import os
from uuid import uuid4

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
)

from ai_engine import generate_ai_response
from wiki_engine import fetch_wikipedia_summary

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

USER_MODES: dict[int, str] = {}
MODES = {
    "smart": "🧠 Smart",
    "funny": "😂 Funny",
    "savage": "😈 Savage",
}


def get_user_mode(user_id: int) -> str:
    return USER_MODES.get(user_id, "smart")


def mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🧠 Smart", callback_data="mode:smart")],
            [InlineKeyboardButton("😂 Funny", callback_data="mode:funny")],
            [InlineKeyboardButton("😈 Savage", callback_data="mode:savage")],
        ]
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = (
        "🤖 *Welcome to Inline AI Bot*\n\n"
        "Use me directly in any chat with inline mode:\n"
        "`@YourBotUsername your question`\n\n"
        "Commands:\n"
        "• /mode - Choose your personality mode\n"
        "• /help - See usage guide"
    )
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = (
        "📘 *How to use*\n\n"
        "1. Type `@YourBotUsername` in any chat.\n"
        "2. Add your query after username.\n"
        "3. Pick result and send.\n\n"
        "✨ I enhance answers using Wikipedia for factual topics when possible.\n"
        "🎭 Use /mode to switch between Smart, Funny, and Savage styles."
    )
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    current_mode = MODES.get(get_user_mode(user_id), "🧠 Smart")
    await update.message.reply_text(
        f"Current mode: *{current_mode}*\n\nSelect a new mode:",
        reply_markup=mode_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )


async def mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    try:
        _, mode = query.data.split(":", maxsplit=1)
        if mode not in MODES:
            await query.edit_message_text("⚠️ Invalid mode selection.")
            return

        user_id = query.from_user.id
        USER_MODES[user_id] = mode
        await query.edit_message_text(
            f"✅ Mode updated to *{MODES[mode]}*", parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        logger.exception("Failed handling mode callback")
        await query.edit_message_text("⚠️ Could not update mode. Please try again.")


async def build_inline_response(user_id: int, query_text: str) -> str:
    mode = get_user_mode(user_id)

    wiki_text = ""
    if query_text and any(
        token in query_text.lower()
        for token in ["what is", "who is", "where is", "when", "history", "define"]
    ):
        wiki_text = await fetch_wikipedia_summary(query_text)

    ai_response = await generate_ai_response(prompt=query_text, mode=mode, wiki_context=wiki_text)

    if wiki_text:
        return (
            f"{ai_response}\n\n"
            f"📚 *Wikipedia Context:*\n{wiki_text}"
        )

    return ai_response


async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inline_query = update.inline_query
    if not inline_query or not inline_query.query:
        return

    user_id = inline_query.from_user.id
    query_text = inline_query.query.strip()

    try:
        response_text = await build_inline_response(user_id=user_id, query_text=query_text)
    except Exception:
        logger.exception("Inline response generation failed")
        response_text = (
            "⚠️ I hit a temporary issue generating a response. "
            "Please try again in a moment."
        )

    safe_text = html.escape(response_text)
    mode_name = MODES.get(get_user_mode(user_id), "🧠 Smart")

    results = [
        InlineQueryResultArticle(
            id=str(uuid4()),
            title=f"{mode_name} Response",
            description=response_text[:100],
            input_message_content=InputTextMessageContent(
                f"{safe_text}",
                parse_mode=ParseMode.HTML,
            ),
        )
    ]

    await inline_query.answer(results=results, cache_time=0, is_personal=True)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception: %s", context.error)


async def post_init(application: Application) -> None:
    me = await application.bot.get_me()
    logger.info("Bot connected as @%s", me.username)


def build_application() -> Application:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is missing. Set it in environment variables.")

    app = ApplicationBuilder().token(token).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("mode", mode_command))
    app.add_handler(CallbackQueryHandler(mode_callback, pattern=r"^mode:"))
    app.add_handler(InlineQueryHandler(inline_query_handler))
    app.add_error_handler(error_handler)
    return app


def main() -> None:
    app = build_application()
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
