import os
import httpx
import logging

logger = logging.getLogger(__name__)

# ── API Keys ──────────────────────────────────────────────────────────────────
GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "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")
CEREBRAS_API_KEY  = os.getenv("CEREBRAS_API_KEY", "csk-rrnt3dppwhtr2222h5evp45x89hfmprh9cdkmpxh3yr8nvv2")
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY", "164b1667-9a55-4eaa-aa39-7f63f252da52")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "AIzaSyDkCXkVQT1xp3lwcVxvEc0sFehQM_sroqA")

# ── Endpoints ─────────────────────────────────────────────────────────────────
GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"
CEREBRAS_URL  = "https://api.cerebras.ai/v1/chat/completions"
SAMBANOVA_URL = "https://api.sambanova.ai/v1/chat/completions"
GEMINI_URL    = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

GROQ_MODEL      = "llama-3.3-70b-versatile"
CEREBRAS_MODEL  = "llama3.1-8b"
SAMBANOVA_MODEL = "Meta-Llama-3.1-8B-Instruct"

# ── Personality Prompts ───────────────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "smart": (
        "You are an intelligent, knowledgeable AI assistant with great personality. "
        "STRICT RULES TO FOLLOW:\n\n"
        "🌐 LANGUAGE: Always reply in the EXACT same language the user used.\n"
        "   - Hindi question → Hindi answer\n"
        "   - English question → English answer\n"
        "   - Hinglish question → Hinglish answer\n\n"
        "📏 ANSWER LENGTH — adapt based on question complexity:\n"
        "   - Simple/factual questions (what is X, who is Y) → 2-3 sentences max\n"
        "   - Medium questions (how does X work, explain Y) → 4-6 sentences with key points\n"
        "   - Complex/deep questions (why, compare, analyze) → detailed answer with structure\n\n"
        "😊 EMOJIS: Use emojis generously and naturally throughout your answer! "
        "Match emojis to the topic — science 🔬, history 📜, sports ⚽, tech 💻, food 🍕, etc.\n\n"
        "✨ QUALITY: Give accurate, insightful, well-structured answers. "
        "Use bullet points (•) for lists. Bold key terms with *asterisks*. "
        "Be engaging and human-like, not robotic.\n\n"
        "📰 If news/wiki context is provided, weave it naturally into your answer."
    ),
    "funny": (
        "You are a hilarious, witty AI comedian who also gives real answers! 😂 "
        "STRICT RULES:\n\n"
        "🌐 LANGUAGE: Always reply in the EXACT same language the user used.\n\n"
        "📏 LENGTH: Match length to question complexity — short for simple, longer for complex.\n\n"
        "😂 HUMOR + EMOJIS: Use TONS of funny emojis! 😂🤣😜🎭💀🫠🤡 "
        "Add jokes, puns, funny observations — but STILL give the real answer!\n\n"
        "✨ STYLE: Be entertaining, use wordplay, funny comparisons. "
        "Make people laugh while learning something! 🎉"
    ),
    "savage": (
        "You are a brutally honest, no-nonsense savage AI! 🔥 "
        "STRICT RULES:\n\n"
        "🌐 LANGUAGE: Always reply in the EXACT same language the user used.\n\n"
        "📏 LENGTH: Match length to question — don't waste words but be thorough when needed.\n\n"
        "🔥 SAVAGE EMOJIS: Use these freely! 🔥💀😤👊🗿⚡🥊😈 "
        "Be bold, direct, cutting — zero sugarcoating!\n\n"
        "✨ STYLE: Roast the topic if needed, be opinionated, confident. "
        "Give real facts with savage delivery. People came for truth, give them truth! 💯"
    ),
}

FALLBACK_RESPONSES = {
    "smart": "🧠 AI thoda busy hai abhi! Ek second baad try karo ⏳",
    "funny": "😂 AI ne chutti le li bhai! Thodi der baad aana 😴💀",
    "savage": "🔥 Sab AI ne kaam chhod diya tera sawal dekh ke. Baad mein aao! 💀",
}


def _build_messages(query: str, mode: str, wiki_context: str = None, news_context: str = None) -> list:
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["smart"])
    user_message = query
    extra = []
    if news_context:
        extra.append(f"📰 Latest News Context:\n{news_context}")
    if wiki_context:
        extra.append(f"📚 Wikipedia Context:\n{wiki_context[:400]}")
    if extra:
        user_message = f"{query}\n\n---\n" + "\n\n".join(extra)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]


async def _call_groq(messages: list, mode: str) -> str | None:
    """1️⃣ Groq — PRIMARY (Llama 3.3 70B, fastest & smartest)"""
    if not GROQ_API_KEY:
        return None
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "max_tokens": 600,
        "temperature": 0.85 if mode in ("funny", "savage") else 0.7,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(GROQ_URL, json=payload, headers=headers)
            if resp.status_code == 429:
                logger.warning("Groq rate limited — skipping")
                return None
            if resp.status_code != 200:
                logger.warning(f"Groq failed [{resp.status_code}]: {resp.text[:150]}")
                return None
            content = resp.json()["choices"][0]["message"]["content"].strip()
            logger.info(f"✅ Groq OK ({len(content)} chars)")
            return content
    except Exception as e:
        logger.warning(f"Groq exception: {type(e).__name__}: {e}")
        return None


async def _call_cerebras(messages: list, mode: str) -> str | None:
    """2️⃣ Cerebras — SECONDARY"""
    if not CEREBRAS_API_KEY:
        return None
    payload = {
        "model": CEREBRAS_MODEL,
        "messages": messages,
        "max_completion_tokens": 600,
        "temperature": 0.85 if mode in ("funny", "savage") else 0.7,
        "top_p": 1,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {CEREBRAS_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(CEREBRAS_URL, json=payload, headers=headers)
            if resp.status_code == 429:
                logger.warning("Cerebras rate limited — skipping")
                return None
            if resp.status_code != 200:
                logger.warning(f"Cerebras failed [{resp.status_code}]: {resp.text[:150]}")
                return None
            content = resp.json()["choices"][0]["message"]["content"].strip()
            logger.info(f"✅ Cerebras OK ({len(content)} chars)")
            return content
    except Exception as e:
        logger.warning(f"Cerebras exception: {type(e).__name__}: {e}")
        return None


async def _call_sambanova(messages: list, mode: str) -> str | None:
    """3️⃣ SambaNova — TERTIARY"""
    if not SAMBANOVA_API_KEY:
        return None
    payload = {
        "model": SAMBANOVA_MODEL,
        "messages": messages,
        "max_tokens": 600,
        "temperature": 0.85 if mode in ("funny", "savage") else 0.7,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {SAMBANOVA_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(SAMBANOVA_URL, json=payload, headers=headers)
            if resp.status_code == 429:
                logger.warning("SambaNova rate limited — skipping")
                return None
            if resp.status_code != 200:
                logger.warning(f"SambaNova failed [{resp.status_code}]")
                return None
            content = resp.json()["choices"][0]["message"]["content"].strip()
            logger.info(f"✅ SambaNova OK ({len(content)} chars)")
            return content
    except Exception as e:
        logger.warning(f"SambaNova exception: {type(e).__name__}: {e}")
        return None


async def _call_gemini(messages: list, mode: str) -> str | None:
    """4️⃣ Gemini — FINAL FALLBACK"""
    if not GEMINI_API_KEY:
        return None
    system_prompt = messages[0]["content"]
    user_text = messages[1]["content"]
    combined = f"{system_prompt}\n\nUser: {user_text}"
    payload = {
        "contents": [{"parts": [{"text": combined}]}],
        "generationConfig": {
            "maxOutputTokens": 600,
            "temperature": 0.85 if mode in ("funny", "savage") else 0.7,
        },
    }
    try:
        url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning(f"Gemini failed [{resp.status_code}]: {resp.text[:150]}")
                return None
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            logger.info(f"✅ Gemini OK ({len(content)} chars)")
            return content
    except Exception as e:
        logger.warning(f"Gemini exception: {type(e).__name__}: {e}")
        return None


async def get_ai_response(
    query: str,
    mode: str = "smart",
    wiki_context: str = None,
    news_context: str = None,
) -> str:
    """
    4-layer fallback chain:
    1️⃣ Groq (Llama 3.3 70B) — PRIMARY ⭐
    2️⃣ Cerebras (Llama 3.1 8B) — SECONDARY
    3️⃣ SambaNova (Llama 3.1 8B) — TERTIARY
    4️⃣ Gemini 2.0 Flash — FINAL FALLBACK
    """
    messages = _build_messages(query, mode, wiki_context, news_context)

    # 1️⃣ Groq — Primary (best quality + speed)
    response = await _call_groq(messages, mode)
    if response:
        return response

    # 2️⃣ Cerebras
    logger.info("Groq failed → trying Cerebras...")
    response = await _call_cerebras(messages, mode)
    if response:
        return response

    # 3️⃣ SambaNova
    logger.info("Cerebras failed → trying SambaNova...")
    response = await _call_sambanova(messages, mode)
    if response:
        return response

    # 4️⃣ Gemini
    logger.info("SambaNova failed → trying Gemini...")
    response = await _call_gemini(messages, mode)
    if response:
        return response

    # ❌ All failed
    logger.error("All 4 AI engines failed!")
    return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
