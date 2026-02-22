import os
import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)

# ── API Keys ──────────────────────────────────────────────────────────────────
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY", "164b1667-9a55-4eaa-aa39-7f63f252da52")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "AIzaSyAwX-T75vih-VIHMA_fH1Dx9RraKfLHsqM")

# ── Endpoints ─────────────────────────────────────────────────────────────────
SAMBANOVA_URL = "https://api.sambanova.ai/v1/chat/completions"
GEMINI_URL    = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Use faster 8B model as primary (30 RPM) and 70B as secondary
SAMBANOVA_FAST_MODEL = "Meta-Llama-3.1-8B-Instruct"   # 30 RPM - faster
SAMBANOVA_SMART_MODEL = "Meta-Llama-3.3-70B-Instruct"  # 20 RPM - smarter

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


async def _call_sambanova(messages: list, mode: str, model: str) -> str | None:
    """Call SambaNova with given model."""
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
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(SAMBANOVA_URL, json=payload, headers=headers)
            if resp.status_code == 429:
                logger.warning(f"SambaNova rate limited on {model}")
                return None
            if resp.status_code != 200:
                logger.warning(f"SambaNova [{model}] failed [{resp.status_code}]: {resp.text[:150]}")
                return None
            content = resp.json()["choices"][0]["message"]["content"].strip()
            logger.info(f"✅ SambaNova [{model}] OK ({len(content)} chars)")
            return content
    except Exception as e:
        logger.warning(f"SambaNova [{model}] exception: {type(e).__name__}: {e}")
        return None


async def _call_gemini(messages: list, mode: str) -> str | None:
    """Call Gemini as final fallback."""
    if not GEMINI_API_KEY:
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
    Smart fallback chain:
    1️⃣ SambaNova 70B (smart/savage/funny)
    2️⃣ SambaNova 8B (if 70B rate limited)
    3️⃣ Gemini 2.0 Flash
    4️⃣ Static message
    """
    messages = _build_messages(query, mode, wiki_context, news_context)

    # 1️⃣ Try SambaNova 70B first (smarter)
    response = await _call_sambanova(messages, mode, SAMBANOVA_SMART_MODEL)
    if response:
        return response

    # 2️⃣ Try SambaNova 8B (faster, higher rate limit)
    logger.info("70B failed → trying SambaNova 8B...")
    response = await _call_sambanova(messages, mode, SAMBANOVA_FAST_MODEL)
    if response:
        return response

    # 3️⃣ Gemini fallback
    logger.info("SambaNova failed → trying Gemini 2.0...")
    response = await _call_gemini(messages, mode)
    if response:
        return response

    # ❌ All failed
    logger.error("All AI engines failed!")
    return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
