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
        "You are a smart AI assistant. "
        "IMPORTANT RULES:\n"
        "1. Always reply in the SAME language the user used. If Hindi → reply Hindi. If English → reply English. If Hinglish → reply Hinglish.\n"
        "2. Keep answers SHORT and TO THE POINT — max 3-4 sentences.\n"
        "3. Use relevant emojis generously to make replies fun and expressive. 🎯✨🔥💡\n"
        "4. No long paragraphs. Be concise and clear.\n"
        "5. If context is provided, use it to enhance your answer briefly."
    ),
    "funny": (
        "You are a witty and funny AI assistant. "
        "IMPORTANT RULES:\n"
        "1. Always reply in the SAME language the user used. If Hindi → reply Hindi. If English → reply English. If Hinglish → reply Hinglish.\n"
        "2. Keep answers SHORT — max 3-4 sentences with humor. 😂\n"
        "3. Use LOTS of funny emojis! 😂🤣😜🎭💀\n"
        "4. Add jokes, puns or funny twists but still answer the question.\n"
        "5. No long boring paragraphs!"
    ),
    "savage": (
        "You are a brutally honest savage AI assistant. "
        "IMPORTANT RULES:\n"
        "1. Always reply in the SAME language the user used. If Hindi → reply Hindi. If English → reply English. If Hinglish → reply Hinglish.\n"
        "2. Keep answers SHORT and BRUTAL — max 3-4 sentences. 🔥\n"
        "3. Use savage emojis! 🔥💀😤👊🗿\n"
        "4. Be bold, direct, no sugarcoating.\n"
        "5. Still answer the question, but with attitude!"
    ),
}

FALLBACK_RESPONSES = {
    "smart": "🧠 AI thoda busy hai abhi! Ek second baad try karo ⏳",
    "funny": "😂 AI ne chutti le li! Thodi der baad aana bhai 😴",
    "savage": "🔥 Sab AI ne kaam chhod diya. Baad mein aao! 💀",
}


def _build_messages(query: str, mode: str, wiki_context: str = None, news_context: str = None) -> list:
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["smart"])
    user_message = query
    extra = []
    if news_context:
        extra.append(f"Latest News (use briefly):\n{news_context}")
    if wiki_context:
        extra.append(f"Wikipedia (use briefly):\n{wiki_context[:300]}")
    if extra:
        user_message = f"Question: {query}\n\n" + "\n\n".join(extra)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]


async def _call_cerebras(messages: list, mode: str) -> str | None:
    if not CEREBRAS_API_KEY:
        return None
    payload = {
        "model": CEREBRAS_MODEL,
        "messages": messages,
        "max_completion_tokens": 200,
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
    if not SAMBANOVA_API_KEY:
        return None
    payload = {
        "model": SAMBANOVA_MODEL,
        "messages": messages,
        "max_tokens": 200,
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
    if not GEMINI_API_KEY:
        return None
    system_prompt = messages[0]["content"]
    user_text = messages[1]["content"]
    combined = f"{system_prompt}\n\nUser: {user_text}"
    payload = {
        "contents": [{"parts": [{"text": combined}]}],
        "generationConfig": {
            "maxOutputTokens": 200,
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
    1️⃣ Cerebras → 2️⃣ SambaNova → 3️⃣ Gemini → Static
    Short answers + same language + more emojis!
    """
    messages = _build_messages(query, mode, wiki_context, news_context)

    response = await _call_cerebras(messages, mode)
    if response:
        return response

    logger.info("Cerebras failed → trying SambaNova...")
    response = await _call_sambanova(messages, mode)
    if response:
        return response

    logger.info("SambaNova failed → trying Gemini...")
    response = await _call_gemini(messages, mode)
    if response:
        return response

    logger.error("All 3 AI engines failed!")
    return FALLBACK_RESPONSES.get(mode, FALLBACK_RESPONSES["smart"])
