import asyncio
import logging
import wikipedia

logger = logging.getLogger(__name__)

# Set language to English
wikipedia.set_lang("en")


async def get_wiki_summary(query: str, sentences: int = 3) -> str | None:
    """
    Asynchronously fetch a Wikipedia summary for the given query.
    Returns summary string or None if not found / error.
    """
    try:
        # Run blocking wikipedia call in executor
        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(
            None, lambda: _fetch_wiki(query, sentences)
        )
        return summary
    except Exception as e:
        logger.warning(f"Wiki fetch unexpected error: {e}")
        return None


def _fetch_wiki(query: str, sentences: int) -> str | None:
    """Blocking Wikipedia fetch function."""
    try:
        summary = wikipedia.summary(query, sentences=sentences, auto_suggest=True)
        return summary
    except wikipedia.exceptions.DisambiguationError as e:
        logger.info(f"Wikipedia disambiguation for '{query}': {e.options[:3]}")
        # Try first option
        try:
            summary = wikipedia.summary(e.options[0], sentences=sentences)
            return summary
        except Exception:
            return None
    except wikipedia.exceptions.PageError:
        logger.info(f"Wikipedia page not found for: '{query}'")
        return None
    except Exception as e:
        logger.warning(f"Wikipedia error: {e}")
        return None
