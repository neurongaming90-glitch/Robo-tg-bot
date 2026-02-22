import os
import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)

# ── API Keys ──────────────────────────────────────────────────────────────────
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY", "164b1667-9a55-4eaa-aa39-7f63f252da52")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")  # ⚠️ Railway variable mein dalo!

# ── Endpoints ─────────────────────────────────────────────────────────────────
SAMBANOVA_URL = "https://api.sambanova.ai/v1/chat/completions"
GEMINI_URL    = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

SAMBANOVA_SMART_MODEL = "Meta-Llama-3.3-70B-Instruct"
SAMBANOVA_FAST_MODEL  = "Meta-Llama-3.1-8B-Instruct"

# ── Personality Prompts ───────────────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "smart": (
        "You are a highly intelligent AI assistant. Provide accurate, detailed, "
        "and well-structured responses. Use facts and clear explanations. "
        "Be professional yet approachable. Keep responses concise but comprehensive. "
        "Always respond in the same language the user asked in."
    ),
    "funny": (
        "You are a witty, humorous AI assistant. Answer questions with jokes, puns, "
        "funny analogies, and a light-hearted tone. Keep it entertaining while still "
        "being helpful. Add relevant emojis and make the user laugh! "
        "Always respond in the same language the user asked in."
    ),
    "savage": (
        "You are a brutally honest, savage AI assistant. Cut through the BS and give "
        "raw, unfiltered truth. Be bold, direct, and unapologetically honest. "
        "Don't sugarcoat anything. Still answer the question, but with brutal honesty. "
        "Always respond in the same language the user asked in."
    ),
}

FALLBACK_RESPONSES = {
    "smart": "🧠 AI engines are busy right now. Please try again in a moment!",
    "funny": "😂 Saare AI so gaye ek saath! Thodi der baad try karo 😴",
    "savage": "🔥 Every AI gave up on you. Impressive. Try again later.",
}


def _build_messages(query: str, mode: str, wiki_context: str = None, news_context: str = None) -> list:
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["smart"])
    user_message = query
    extra = []
    if news_context:
        extra.append(f"Latest News:\n{news_context}")
    if wiki_context:
        extra.append(f"Wikipedia context:\n{wiki_context}")
    if extra:
        user_message = f"Question: {query}\n\n" + "\n\n".join(extra) + "\n\nUse this context if relevant."
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]


async def _call_sambanova(messages: list, mode: str, model: str, retry: int = 2) -> str | None:
    """Call SambaNova with automatic retry on rate limit."""
    if not SAMBANOVA_API_KEY:
        return None
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.8 if mode in ("funny", "savage") else 0.6,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {SAMBANOVA_API_KEY}",
        "Content-Type": "application/json",
    }
    for attempt in range(retry):
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(SAMBANOVA_URL, json=payload, headers=headers)
                if resp.status_code == 429:
                    wait = 3 * (attempt + 1)
                    logger.warning(f"SambaNova rate limit [{model}] — waiting {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code != 200:
                    logger.warning(f"SambaNova [{model}] failed [{resp.status_code}]")
                    return None
                content = resp.json()["choices"][0]["message"]["content"].strip()
                logger.info(f"✅ SambaNova [{model}] OK ({len(content)} chars)")
                return content
        except Exception as e:
            logger.warning(f"SambaNova [{model}] exception: {type(e).__name__}: {e}")
            return None
    return None


async def _call_gemini(messages: list, mode: str) -> str | None:
    """Call Gemini 2.0 Flash as fallback."""
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set in environment!")
        return None
    system_prompt = messages[0]["content"]
    user_text = messages[1]["content"]
    combined = f"{system_prompt}\n\nUser: {user_text}"
    payload = {
        "contents": [{"parts": [{"text": combined}]}],
        "generationConfig": {
            "maxOutputTokens": 500,
            "temperature": 0.8 if mode in ("funny", "savage") else 0.6,
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
    Smart fallback chain with retry:
    1️⃣ SambaNova 70B (retry x2)
    2️⃣ SambaNova 8B (retry x2)
    3️⃣ Gemini 2.0 Flash
    4️⃣ Static message
    """
    messages = _build_messages(query, mode, wiki_context, news_context)

    # 1️⃣ SambaNova 70B
    response = await _call_sambanova(messages, mode, SAMBANOVA_SMART_MODEL, retry=2)
    if response:
        return response

    # 2️⃣ SambaNova 8B
    logger.info("70B failed → trying SambaNova 8B...")
    response = await _call_sambanova(messages, mode, SAMBANOVA_FAST_MODEL, retry=2)
    if response:
        return response

    # 3️⃣ Gemini 2.0 Flash
    logger.info("SambaNova failed → trying Gemini 2.0...")
    response = await _call_gemini(messages, mode)
    if response:
        return response

    # ❌ All failed
    logger.error("All AI engines failed!")
    return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
