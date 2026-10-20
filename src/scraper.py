"""Scraper module for Nogizaka Colors official website.

Extracts high-resolution member photos using Python's built-in html.parser
to maintain zero-external-dependency portability.
"""

from html.parser import HTMLParser
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests

from src.config import DEFAULT_HEADERS, GALLERY_URL_TEMPLATE


class GalleryImageParser(HTMLParser):
    """HTML Parser designed to extract image source URLs from gallery pages."""

    def __init__(self) -> None:
        super().__init__()
        self.img_urls: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        """Handle <img> tags and extract src or lazy-loaded data-src attributes."""
        if tag.lower() == "img":
            attrs_dict: Dict[str, str] = dict(attrs)
            src = attrs_dict.get("src") or attrs_dict.get("data-src")
            if src:
                self.img_urls.append(src.strip())


def extract_photo_urls(html_content: str, base_url: str) -> List[str]:
    """Parse raw HTML content and return filtered high-resolution gallery URLs.

    Excludes website chrome, social navigation icons, OGP meta images, and logos.
    """
    parser = GalleryImageParser()
    parser.feed(html_content)

    filtered_urls: List[str] = []
    ignored_keywords = ["logo", "common", "assets", "ogp", "icon", "banner"]

    for raw_src in parser.img_urls:
        full_url = urljoin(base_url, raw_src)
        lower_url = full_url.lower()

        # Target authentic high-resolution content photos under /images/46/
        if "/images/46/" in lower_url and not any(kw in lower_url for kw in ignored_keywords):
            if full_url not in filtered_urls:
                filtered_urls.append(full_url)

    return filtered_urls


def get_member_photos(
    member_id: str,
    max_retries: int = 3,
    timeout: int = 15,
    headers: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Fetch all photo URLs from a member's Nogizaka Colors gallery page.

    Args:
        member_id: Numeric member ID string (e.g. '63110').
        max_retries: Number of connection retry attempts.
        timeout: Request timeout in seconds.
        headers: Optional HTTP headers dictionary.

    Returns:
        List of absolute image URLs.
    """
    gallery_url = GALLERY_URL_TEMPLATE.format(member_id=member_id)
    req_headers = headers or DEFAULT_HEADERS

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(gallery_url, headers=req_headers, timeout=timeout)
            if response.status_code == 200:
                return extract_photo_urls(response.text, gallery_url)
            print(f"  [-] Percobaan {attempt}/{max_retries}: HTTP {response.status_code} saat mengakses {gallery_url}")
        except Exception as exc:
            print(f"  [-] Percobaan {attempt}/{max_retries} error: {exc}")

        if attempt < max_retries:
            time.sleep(2.0)

    return []


def download_image(
    url: str,
    max_retries: int = 3,
    timeout: int = 20,
    headers: Optional[Dict[str, str]] = None,
) -> Optional[bytes]:
    """Download raw image bytes directly into memory without saving to disk.

    Args:
        url: Absolute URL of the image.
        max_retries: Number of download retry attempts.
        timeout: Request timeout in seconds.
        headers: Optional HTTP headers dictionary.

    Returns:
        Raw bytes of the image if successful, None otherwise.
    """
    req_headers = headers or DEFAULT_HEADERS
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=req_headers, timeout=timeout)
            if response.status_code == 200:
                return response.content
        except Exception:
            pass

        if attempt < max_retries:
            time.sleep(1.5)

    return None
