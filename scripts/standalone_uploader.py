#!/usr/bin/env python3
"""Standalone Nogizaka Colors -> Discord Thread Uploader (Single-File Edition).

Zero third-party HTML parsing dependencies (uses built-in html.parser).
Streams images directly in-memory to prevent disk waste.
Handles Discord HTTP 429 (Rate Limits) and HTTP 413 (Payload Too Large auto-split).
"""

from html.parser import HTMLParser
import json
import os
import sys
import time
from typing import List, Optional, Tuple
from urllib.parse import urljoin

import requests

# Set stdout encoding to utf-8 for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Optional .env loading if python-dotenv is installed
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# ==============================================================================
# KONFIGURASI WEBHOOK DISCORD & THREAD (DAPAT DIISI LEWAT .ENV / TERMINAL)
# ==============================================================================
# Diambil dari environment variable atau prompt interaktif saat dijalankan
DEFAULT_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")
DEFAULT_THREAD = os.getenv("DISCORD_THREAD_ID", "")

# Daftar 11 Member Generasi ke-6 Nogizaka46 (Nogizaka Colors Campaign)
MEMBERS = [
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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


class ImgParser(HTMLParser):
    """HTML Parser bawaan Python untuk mendeteksi tag <img> tanpa dependensi bs4."""

    def __init__(self) -> None:
        super().__init__()
        self.img_urls: List[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag.lower() == "img":
            attrs_dict = dict(attrs)
            src = attrs_dict.get("src") or attrs_dict.get("data-src")
            if src:
                self.img_urls.append(src.strip())


def get_member_photos(member_id: str) -> List[str]:
    """Mengambil semua URL foto galeri member dari situs resmi Nogizaka46."""
    gallery_url = f"https://www.nogizaka46.com/s/n46/gallery/ngColors_{member_id}"
    print(f"  [+] Mengakses galeri resmi: {gallery_url}")

    for attempt in range(1, 4):
        try:
            resp = requests.get(gallery_url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                parser = ImgParser()
                parser.feed(resp.text)

                photo_urls: List[str] = []
                for src in parser.img_urls:
                    full_url = urljoin(gallery_url, src)
                    lower_url = full_url.lower()
                    if "/images/46/" in lower_url and not any(
                        x in lower_url for x in ["logo", "common", "assets", "ogp", "icon"]
                    ):
                        if full_url not in photo_urls:
                            photo_urls.append(full_url)
                return photo_urls
            print(f"  [-] Percobaan {attempt}: HTTP {resp.status_code}")
        except Exception as err:
            print(f"  [-] Percobaan {attempt} error: {err}")
        time.sleep(2.0)

    return []


def download_image(url: str, max_retries: int = 3) -> Optional[bytes]:
    """Mengunduh byte gambar langsung ke memori (in-memory streaming)."""
    for _ in range(max_retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                return resp.content
        except Exception:
            time.sleep(1.5)
    return None


def send_to_discord(
    webhook_url: str,
    thread_id: Optional[str] = None,
    content: Optional[str] = None,
    file_items: Optional[List[Tuple[str, bytes]]] = None,
    max_retries: int = 5,
) -> bool:
    """Mengunggah pesan atau berkas ke Discord Webhook thread dengan manajemen 429 & 413."""
    # Guard against completely empty requests that trigger Discord HTTP 400
    if not content and not file_items:
        print("  [-] Error: Tidak ada konten teks atau berkas untuk dikirim ke Discord.")
        return False

    if thread_id:
        separator = "&" if "?" in webhook_url else "?"
        url = f"{webhook_url}{separator}thread_id={thread_id}"
    else:
        url = webhook_url

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

    for _ in range(max_retries):
        try:
            response = requests.post(url, data=data, files=files if files else None, timeout=45)
            if response.status_code in [200, 204]:
                return True
            elif response.status_code == 429:
                try:
                    retry_after = float(response.json().get("retry_after", 3.0))
                except Exception:
                    retry_after = 3.0
                print(f"  [!] Discord Rate Limit hit (429). Menunggu {retry_after + 0.5:.1f} detik...")
                time.sleep(retry_after + 0.5)
                continue
            elif response.status_code == 413:
                print(f"  [!] HTTP 413 Payload Too Large! Ukuran batch terlalu besar ({len(file_items or [])} file).")
                # Jika batch bisa dipecah, pecah menjadi dua bagian
                if file_items and len(file_items) > 1:
                    mid = len(file_items) // 2
                    part1 = file_items[:mid]
                    part2 = file_items[mid:]
                    print(f"  [+] Memecah batch menjadi 2 bagian ({len(part1)} dan {len(part2)} foto)...")
                    ok1 = send_to_discord(webhook_url, thread_id, content=content, file_items=part1)
                    time.sleep(2.0)
                    ok2 = send_to_discord(webhook_url, thread_id, content=None, file_items=part2)
                    return ok1 and ok2
                print("  [-] File tunggal melebihi kuota upload Discord!")
                return False
            else:
                print(f"  [-] Discord HTTP {response.status_code}: {response.text}")
                time.sleep(2.0)
        except Exception as e:
            print(f"  [-] Request exception: {e}")
            time.sleep(2.0)

    return False


def main() -> None:
    print("=" * 65)
    print("🌸 NOGIZAKA COLORS (GEN 6) -> DISCORD UPLOADER (STANDALONE)")
    print("=" * 65)

    webhook_url = DEFAULT_WEBHOOK
    thread_id = DEFAULT_THREAD

    # Minta input jika belum ada di environment
    if not webhook_url or "your_webhook_token_here" in webhook_url:
        print("\n[!] Variabel DISCORD_WEBHOOK_URL belum dikonfigurasi.")
        webhook_url = input("Masukkan Webhook Discord URL: ").strip()
        if not webhook_url:
            print("[-] URL Webhook wajib diisi! Program dihentikan.")
            return

    if not thread_id:
        thread_input = input("Masukkan Thread ID target (opsional, tekan Enter jika tanpa thread): ").strip()
        if thread_input:
            thread_id = thread_input

    print(f"\nTarget Thread ID : {thread_id or 'Tanpa Thread (Channel Utama)'}")
    print(f"Total Member     : {len(MEMBERS)} Orang\n")

    total_uploaded_photos = 0
    has_errors = False
    start_time = time.time()

    for i, m in enumerate(MEMBERS, 1):
        name_title = f"{m['kanji']} ({m['romaji']})"
        print(f"\n[{i}/{len(MEMBERS)}] Memproses: {name_title} [ID: {m['id']}]")

        photos = get_member_photos(m["id"])
        total_photos = len(photos)
        print(f"  [✓] Terdeteksi {total_photos} foto di galeri resmi.")

        if total_photos == 0:
            print(f"  [-] Lewati {m['romaji']} karena foto tidak ditemukan.")
            continue

        # 1. Kirim pesan pengantar identitas member
        header_text = (
            f"## 🌸 {m['kanji']} / {m['romaji']} (Nogizaka Colors)\n"
            f"**Total galeri resmi:** {total_photos} foto\n"
            f"*Sumber: https://www.nogizaka46.com/s/n46/gallery/ngColors_{m['id']}*"
        )
        print("  [↑] Mengirim header identitas member...")
        header_ok = send_to_discord(webhook_url, thread_id, content=header_text)
        if not header_ok:
            print(f"  [-] Peringatan: Gagal mengirim header untuk {m['romaji']}!")
            has_errors = True
        time.sleep(2.0)

        # 2. Unduh dan kelompokkan foto (Dynamic Smart Batching)
        current_batch: List[Tuple[str, bytes]] = []
        current_batch_bytes = 0
        batch_index = 1
        member_uploaded = 0

        for idx, p_url in enumerate(photos, 1):
            ext = "png" if ".png" in p_url.lower() else "jpg"
            fname = f"{m['romaji'].replace(' ', '_')}_{idx:02d}.{ext}"

            print(f"  [↓] Mengunduh foto {idx:02d}/{total_photos:02d} ({fname})...")
            img_data = download_image(p_url)

            if not img_data:
                print(f"  [-] Gagal mengunduh foto {idx:02d}, dilewati.")
                has_errors = True
                continue

            img_size = len(img_data)

            # Jika menambahkan foto ini melebihi 6 foto atau melebihi 8.5 MB, kirim batch dulu
            if current_batch and (len(current_batch) >= 6 or (current_batch_bytes + img_size) > 8500000):
                mb_size = current_batch_bytes / (1024 * 1024)
                print(f"  [↑] Mengunggah Batch {batch_index} ({len(current_batch)} foto, {mb_size:.2f} MB)...")
                batch_ok = send_to_discord(webhook_url, thread_id, file_items=current_batch)
                if batch_ok:
                    member_uploaded += len(current_batch)
                    total_uploaded_photos += len(current_batch)
                else:
                    print(f"  [-] Gagal mengunggah Batch {batch_index} ({len(current_batch)} foto) ke Discord!")
                    has_errors = True
                batch_index += 1
                current_batch = []
                current_batch_bytes = 0
                time.sleep(2.0)

            current_batch.append((fname, img_data))
            current_batch_bytes += img_size

        # Kirim sisa foto di batch terakhir
        if current_batch:
            mb_size = current_batch_bytes / (1024 * 1024)
            print(f"  [↑] Mengunggah Batch {batch_index} ({len(current_batch)} foto, {mb_size:.2f} MB)...")
            batch_ok = send_to_discord(webhook_url, thread_id, file_items=current_batch)
            if batch_ok:
                member_uploaded += len(current_batch)
                total_uploaded_photos += len(current_batch)
            else:
                print(f"  [-] Gagal mengunggah Batch {batch_index} ({len(current_batch)} foto) ke Discord!")
                has_errors = True
            time.sleep(2.0)

        if member_uploaded == total_photos:
            print(f"  [✓] Sukses mengunggah seluruh foto untuk {m['romaji']}!")
        else:
            print(f"  [!] Arsip {m['romaji']} parsial: {member_uploaded}/{total_photos} terunggah.")
        time.sleep(1.5)

    elapsed = time.time() - start_time
    print("\n" + "=" * 65)
    if has_errors:
        print(f"⚠️ SELESAI DENGAN CATATAN: Total {total_uploaded_photos} foto terunggah (beberapa item gagal).")
    else:
        print(f"🎉 SELESAI! Total {total_uploaded_photos} foto berhasil diunggah ke Discord.")
    print(f"⏱ Waktu pengerjaan: {elapsed:.1f} detik ({elapsed/60:.1f} menit).")
    print("=" * 65)


if __name__ == "__main__":
    main()
