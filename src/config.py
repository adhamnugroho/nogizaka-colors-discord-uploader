"""Configuration module for Nogizaka Colors Discord Uploader."""

import os
from typing import Any, Dict, List, Optional

# Load environment variables from .env file if python-dotenv is available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Discord Webhook & Target Thread Settings
DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
DISCORD_THREAD_ID: str = os.getenv("DISCORD_THREAD_ID", "").strip()

# Operational Tuning Constants
DEFAULT_RATE_LIMIT_DELAY: float = float(os.getenv("RATE_LIMIT_DELAY", "2.0"))
MAX_BATCH_FILES: int = int(os.getenv("MAX_BATCH_FILES", "6"))
MAX_BATCH_BYTES: int = int(os.getenv("MAX_BATCH_BYTES", "8500000"))  # ~8.5 MB

# Standard Browser User-Agent Header
DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

# Base Gallery URL Template
GALLERY_URL_TEMPLATE: str = "https://www.nogizaka46.com/s/n46/gallery/ngColors_{member_id}"

# 11 Official 6th Generation Nogizaka46 Members (Nogizaka Colors Campaign)
# Verified authentic Kanji and official Romaji spellings
MEMBERS: List[Dict[str, Any]] = [
    {"id": "63102", "kanji": "大越 ひなの", "romaji": "Hinano Okoshi"},
    {"id": "63104", "kanji": "海邉 朱莉", "romaji": "Akari Kaibe"},
    {"id": "63106", "kanji": "鈴木 佑捺", "romaji": "Yuna Suzuki"},
    {"id": "63110", "kanji": "森平 麗心", "romaji": "Urumi Morihira"},
    {"id": "63103", "kanji": "小津 玲奈", "romaji": "Reina Ozu"},
    {"id": "63108", "kanji": "長嶋 凛桜", "romaji": "Rio Nagashima"},
    {"id": "63101", "kanji": "愛宕 心響", "romaji": "Kokone Atago"},
    {"id": "63105", "kanji": "川端 晃菜", "romaji": "Hina Kawabata"},
    {"id": "63109", "kanji": "増田 三莉音", "romaji": "Mirine Masuda"},
    {"id": "63107", "kanji": "瀬戸口 心月", "romaji": "Mitsuki Setoguchi"},
    {"id": "63111", "kanji": "矢田 萌華", "romaji": "Moeka Yada"},
]


def validate_config(webhook_url: Optional[str] = None) -> bool:
    """Validate webhook URL and configuration.

    Args:
        webhook_url: Optional webhook URL to test. Defaults to DISCORD_WEBHOOK_URL.

    Returns:
        True if webhook URL is non-empty, contains valid schema, and is not a placeholder.
    """
    url = (webhook_url if webhook_url is not None else DISCORD_WEBHOOK_URL).strip()
    if not url:
        return False
    if "your_webhook_token_here" in url or "your_actual_token" in url:
        return False
    if not (url.startswith("https://") or url.startswith("http://")):
        return False
    return True
