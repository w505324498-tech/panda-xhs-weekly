"""Deduplication utilities for news and GitHub items."""


def dedupe_by_url(items: list[dict]) -> list[dict]:
    """Remove items with duplicate 'url' keys, preserving order."""
    seen: set[str] = set()
    result: list[dict] = []
    for item in items:
        url = (item.get("url") or "").strip()
        if not url:
            continue
        if url in seen:
            continue
        seen.add(url)
        result.append(item)
    return result


def dedupe_by_title(items: list[dict], threshold: float = 0.6) -> list[dict]:
    """
    Remove near-duplicate items based on title word overlap.
    Uses Jaccard similarity on words — much better than character-level for news titles.
    """
    import re

    def _tokenize(s: str) -> set[str]:
        """Tokenize a title into lowercase word tokens."""
        return set(re.findall(r"[a-zA-Z0-9一-鿿]+", s.lower()))

    seen: list[set[str]] = []
    result: list[dict] = []
    for item in items:
        title = item.get("title", "")
        if not title.strip():
            continue
        tokens = _tokenize(title)
        if not tokens:
            result.append(item)
            continue
        is_dup = False
        for s in seen:
            if not s:
                continue
            overlap = len(tokens & s) / len(tokens | s)
            if overlap > threshold:
                is_dup = True
                break
        if not is_dup:
            seen.append(tokens)
            result.append(item)
    return result
