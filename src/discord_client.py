"""Discord Webhook Client module.

Handles multipart uploads, thread routing via ?thread_id=, adaptive rate limiting
(HTTP 429 retry_after), and automatic payload-splitting fallback (HTTP 413).
"""

import json
import time
from typing import List, Optional, Tuple

import requests


class DiscordWebhookClient:
    """Robust client for sending messages and media batches to Discord via Webhooks."""

    def __init__(self, webhook_url: str, thread_id: Optional[str] = None) -> None:
        """Initialize the client with webhook URL and optional thread ID.

        Args:
            webhook_url: Full Discord Webhook URL.
            thread_id: Optional Discord thread ID target.
        """
        self.webhook_url = webhook_url.strip()
        self.thread_id = thread_id.strip() if thread_id else None

    @property
    def endpoint_url(self) -> str:
        """Construct endpoint URL with thread_id query parameter if provided."""
        if self.thread_id:
            separator = "&" if "?" in self.webhook_url else "?"
            return f"{self.webhook_url}{separator}thread_id={self.thread_id}"
        return self.webhook_url

    def send_message(
        self,
        content: Optional[str] = None,
        file_items: Optional[List[Tuple[str, bytes]]] = None,
        max_retries: int = 5,
    ) -> bool:
        """Send a formatted text message and/or batch of files to Discord.

        Args:
            content: Markdown formatted message content.
            file_items: List of (filename, file_bytes) tuples.
            max_retries: Number of retry attempts for network hiccups or rate limits.

        Returns:
            True if all content was successfully received by Discord, False otherwise.
        """
        # Guard against completely empty requests that trigger Discord HTTP 400
        if not content and not file_items:
            print("  [-] Error: Tidak ada konten teks atau berkas untuk dikirim ke Discord.")
            return False

        payload = {}
        if content:
            payload["content"] = content

        data = {"payload_json": json.dumps(payload)} if payload else {}

        files = {}
        if file_items:
            for idx, (filename, file_bytes) in enumerate(file_items):
                lower_fn = filename.lower()
                if lower_fn.endswith(".png"):
                    mime_type = "image/png"
                elif lower_fn.endswith(".webp"):
                    mime_type = "image/webp"
                elif lower_fn.endswith(".gif"):
                    mime_type = "image/gif"
                else:
                    mime_type = "image/jpeg"
                files[f"files[{idx}]"] = (filename, file_bytes, mime_type)

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    self.endpoint_url,
                    data=data,
                    files=files if files else None,
                    timeout=45,
                )

                # HTTP 200 (OK) or 204 (No Content) indicate complete success
                if response.status_code in [200, 204]:
                    return True

                # HTTP 429: Rate Limit Encountered
                if response.status_code == 429:
                    try:
                        retry_after = float(response.json().get("retry_after", 3.0))
                    except Exception:
                        retry_after = 3.0
                    sleep_duration = retry_after + 0.5
                    print(f"  [!] Discord Rate Limit (429). Menunggu {sleep_duration:.1f} detik...")
                    time.sleep(sleep_duration)
                    continue

                # HTTP 413: Payload Too Large
                if response.status_code == 413:
                    print(
                        f"  [!] HTTP 413 Payload Too Large! "
                        f"Ukuran batch terlalu besar ({len(file_items or [])} berkas)."
                    )
                    # Automatically bisect the batch into two halves and send sequentially
                    if file_items and len(file_items) > 1:
                        mid = len(file_items) // 2
                        part1 = file_items[:mid]
                        part2 = file_items[mid:]
                        print(f"  [+] Memecah batch menjadi 2 bagian ({len(part1)} dan {len(part2)} foto)...")
                        # Preserve message content with the first chunk
                        ok1 = self.send_message(content=content, file_items=part1)
                        time.sleep(2.0)
                        ok2 = self.send_message(content=None, file_items=part2)
                        return ok1 and ok2
                    print("  [-] Berkas tunggal melebihi kuota upload Discord!")
                    return False

                # Unexpected status codes
                print(f"  [-] Discord HTTP {response.status_code}: {response.text}")
                time.sleep(2.0)

            except Exception as exc:
                print(f"  [-] Percobaan {attempt}/{max_retries} koneksi error: {exc}")
                time.sleep(2.0)

        return False
