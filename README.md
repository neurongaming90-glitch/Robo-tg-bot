# Telegram Inline AI Bot (DeepSeek + Wikipedia)

Production-ready inline Telegram bot built with async `python-telegram-bot` (v20+ style), powered by DeepSeek and enhanced with Wikipedia summaries.

## Features

- Inline mode support (`@botusername your query`)
- DeepSeek `deepseek-chat` model integration
- Personality modes per user:
  - 🧠 Smart (default)
  - 😂 Funny
  - 😈 Savage
- `/mode` command with inline keyboard switching
- `/start`, `/help`, `/mode` commands
- Wikipedia summary enhancement for factual queries
- Graceful fallback responses on API failure
- Railway-ready deployment files

## Project Structure

```text
.
├── ai_engine.py
├── main.py
├── wiki_engine.py
├── requirements.txt
├── Procfile
├── runtime.txt
└── README.md
```

## Environment Variables

Set these on Railway (or locally):

- `BOT_TOKEN` = your Telegram bot token
- `DEEPSEEK_API_KEY` = your DeepSeek API key

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN="your_bot_token"
export DEEPSEEK_API_KEY="your_deepseek_key"
python main.py
```

## Railway Deployment

1. Push this project to a GitHub repository.
2. Create a new Railway project from the repo.
3. Add environment variables:
   - `BOT_TOKEN`
   - `DEEPSEEK_API_KEY`
4. Railway will use:
   - `Procfile` (`worker: python main.py`)
   - `runtime.txt` (Python 3.11.9)
5. Deploy.

## Notes

- This bot uses polling mode for simplicity and reliability on Railway worker dynos.
- User mode storage is in-memory; restarting the process resets user modes.
