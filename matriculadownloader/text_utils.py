import os
import re
import webbrowser


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def safe_name(text: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', '_', text.strip())
    return ''.join(ch if ch.isprintable() else '_' for ch in cleaned)


def parse_pages(pages_str: str, total: int) -> list[int]:
    if not pages_str.strip():
        return list(range(1, total + 1))

    result: list[int] = []
    for part in pages_str.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            try:
                start, end = map(int, part.split('-', 1))
                result.extend(range(start, end + 1))
            except Exception:
                continue
        else:
            try:
                result.append(int(part))
            except Exception:
                continue

    return [page for page in sorted(set(result)) if 1 <= page <= total]


def open_homepage() -> None:
    webbrowser.open('https://data.matricula-online.eu/de/bestande/')
