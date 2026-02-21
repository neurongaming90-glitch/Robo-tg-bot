import asyncio

import wikipedia
from wikipedia.exceptions import DisambiguationError, PageError


def _wiki_lookup_sync(query: str) -> str:
    topic = query.strip()
    if not topic:
        return ""

    try:
        wikipedia.set_lang("en")
        return wikipedia.summary(topic, sentences=2, auto_suggest=True)
    except DisambiguationError as exc:
        options = ", ".join(exc.options[:5])
        return f"Ambiguous topic. Possible options: {options}."
    except PageError:
        return ""
    except Exception:
        return ""


async def fetch_wikipedia_summary(query: str) -> str:
    return await asyncio.to_thread(_wiki_lookup_sync, query)
