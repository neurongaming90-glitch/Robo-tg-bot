import os
import httpx
import logging

logger = logging.getLogger(__name__)

# ── API Keys ──────────────────────────────────────────────────────────────────
CEREBRAS_API_KEY  = os.getenv("CEREBRAS_API_KEY", "csk-rrnt3dppwhtr2222h5evp45x89hfmprh9cdkmpxh3yr8nvv2")
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY", "164b1667-9a55-4eaa-aa39-7f63f252da52")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "AIzaSyDkCXkVQT1xp3lwcVxvEc0sFehQM_sroqA")

# ── Endpoints ─────────────────────────────────────────────────────────────────
CEREBRAS_URL  = "https://api.cerebras.ai/v1/chat/completions"
SAMBANOVA_URL = "https://api.sambanova.ai/v1/chat/completions"
GEMINI_URL    = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

CEREBRAS_MODEL  = "llama3.1-8b"
SAMBANOVA_MODEL = "Meta-Llama-3.1-8B-Instruct"

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
    "savage": "🔥 Every AI gave up on your question. Try again later.",
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


async def _call_cerebras(messages: list, mode: str) -> str | None:
    """Call Cerebras — Llama 3.3 70B, super fast, no rate limit issues."""
    if not CEREBRAS_API_KEY:
        return None
    payload = {
        "model": CEREBRAS_MODEL,
        "messages": messages,
        "max_completion_tokens": 500,
        "temperature": 0.8 if mode in ("funny", "savage") else 0.6,
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
    """Call SambaNova as 2nd fallback."""
    if not SAMBANOVA_API_KEY:
        return None
    payload = {
        "model": SAMBANOVA_MODEL,
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
    Triple fallback — instant switch on failure:
    1️⃣ Cerebras (Llama 3.3 70B) — fastest
    2️⃣ SambaNova (Llama 3.1 8B) — backup
    3️⃣ Gemini 2.0 Flash — final fallback
    """
    messages = _build_messages(query, mode, wiki_context, news_context)

    # 1️⃣ Cerebras — primary (fastest)
    response = await _call_cerebras(messages, mode)
    if response:
        return response

    # 2️⃣ SambaNova — secondary
    logger.info("Cerebras failed → trying SambaNova...")
    response = await _call_sambanova(messages, mode)
    if response:
        return response

    # 3️⃣ Gemini — final
    logger.info("SambaNova failed → trying Gemini...")
    response = await _call_gemini(messages, mode)
    if response:
        return response

    # ❌ All failed
    logger.error("All 3 AI engines failed!")
    return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
