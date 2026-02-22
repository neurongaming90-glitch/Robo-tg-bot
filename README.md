# 🤖 Telegram Inline AI Bot

A production-ready Telegram inline bot powered by **DeepSeek AI** and **Wikipedia**, with personality modes and Railway.app deployment support.

---

## ✨ Features

- **Inline Mode** — Works via `@botname query` in any Telegram chat
- **DeepSeek AI** — Smart AI-powered responses
- **Wikipedia Integration** — Factual context enhancement
- **3 Personality Modes** — Smart 🧠 | Funny 😂 | Savage 🔥
- **Mode Switching** — `/mode` command with inline keyboard buttons
- **Graceful Fallbacks** — Never crashes on API errors
- **Railway Ready** — Deploy in minutes

---

## 📁 Project Structure

```
tg_bot_project/
├── main.py          # Bot logic, handlers, inline query
├── ai_engine.py     # DeepSeek API integration
├── wiki_engine.py   # Wikipedia summary fetcher
├── requirements.txt
├── Procfile         # Railway deployment
├── runtime.txt      # Python version
└── README.md
```

---

## 🚀 Deployment on Railway.app

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/your-repo.git
git push -u origin main
```

### 2. Create Railway Project
- Go to [railway.app](https://railway.app)
- Click **New Project → Deploy from GitHub Repo**
- Select your repository

### 3. Set Environment Variables
In Railway dashboard → your service → **Variables**, add:

| Variable | Value |
|----------|-------|
| `BOT_TOKEN` | Your Telegram Bot Token |
| `DEEPSEEK_API_KEY` | Your DeepSeek API Key |

### 4. Enable Inline Mode on BotFather
- Message `@BotFather` on Telegram
- `/setinline` → Select your bot → Set a placeholder (e.g. "Ask me anything...")

### 5. Deploy!
Railway auto-deploys on push. Your bot will be live! ✅

---

## 🧪 Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export BOT_TOKEN="your_bot_token"
export DEEPSEEK_API_KEY="your_deepseek_key"

# Run bot
python main.py
```

---

## 🎭 Personality Modes

| Mode | Style |
|------|-------|
| 🧠 Smart | Detailed, informative, professional |
| 😂 Funny | Witty, humorous, emoji-filled |
| 🔥 Savage | Brutally honest, bold, no BS |

Switch modes with `/mode` command.

---

## 💬 Usage

1. Open any Telegram chat
2. Type `@YourBotUsername what is quantum computing?`
3. Select the result — the AI response is sent!

---

## 🛠 Tech Stack

- **Python 3.11**
- **python-telegram-bot v21** (async)
- **DeepSeek API** (deepseek-chat model)
- **Wikipedia Python Library**
- **httpx** (async HTTP client)
- **Railway.app** (hosting)

---

## ⚙️ Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram Bot Token from @BotFather | ✅ |
| `DEEPSEEK_API_KEY` | DeepSeek API key | ✅ |

> ⚠️ Never hardcode API keys. Always use environment variables in production.

---

## 📝 Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/mode` | Switch personality mode |
| `/help` | Help and usage info |
