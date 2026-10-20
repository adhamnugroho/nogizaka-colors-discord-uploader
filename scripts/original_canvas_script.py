#!/usr/bin/env python3
"""Arsip Skrip Awal Gemini Canvas: Nogizaka Colors Discord Uploader.

CATATAN HISTORIS:
Berkas ini adalah implementasi purwarupa awal yang dihasilkan pada sesi Gemini Web & Canvas.
Versi ini membutuhkan dependensi eksternal 'beautifulsoup4' dan menggunakan batching statis
10 foto per pesan, yang kemudian disempurnakan oleh engine modular robust di folder src/
dan scripts/standalone_uploader.py.

PENTING:
Token webhook asli telah disamarkan demi keamanan.
"""

import json
import os
import sys
import time
from urllib.parse import urljoin

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # Handled gracefully in get_member_photos()
import requests

# ==============================================================================
# KONFIGURASI WEBHOOK DISCORD (DISAMARKAN UNTUK KEAMANAN REPOSITORI)
# ==============================================================================
# Silakan isi variabel lingkungan DISCORD_WEBHOOK_URL atau ganti string di bawah ini
WEBHOOK_URL = os.getenv(
    "DISCORD_WEBHOOK_URL",
    "https://discord.com/api/webhooks/123456789012345678/your_webhook_token_here",
)
THREAD_ID = os.getenv("DISCORD_THREAD_ID", "1561792308255391844")  # Thread: Nogizaka Colors (Gen 6)

# Daftar 11 Member Generasi ke-6 Nogizaka46 (sesuai urutan rilis di Nogizaka Colors)
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
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def get_member_photos(member_id):
    """Mengambil semua URL foto galeri member dari situs Nogizaka46."""
    if BeautifulSoup is None:
        print("  [-] Error: Script purwarupa historis ini membutuhkan paket 'beautifulsoup4'.")
        print("      Silakan jalankan: pip install beautifulsoup4")
        print("      Atau gunakan skrip modern zero-dependency: python scripts/standalone_uploader.py")
        return []

    gallery_url = f"https://www.nogizaka46.com/s/n46/gallery/ngColors_{member_id}"
    print(f"  [+] Mengakses galeri: {gallery_url}")

    try:
        resp = requests.get(gallery_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  [-] Gagal mengakses ({resp.status_code})")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        photo_urls = []

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if not src:
                continue

            full_url = urljoin(gallery_url, src)

            # Filter hanya foto konten (bukan ikon media sosial atau logo navigasi)
            if "/images/46/" in full_url and not any(x in full_url.lower() for x in ["logo", "common", "assets", "ogp"]):
                if full_url not in photo_urls:
                    photo_urls.append(full_url)

        return photo_urls
    except Exception as e:
        print(f"  [-] Terjadi error saat scraping: {e}")
        return []


def send_to_discord(content=None, file_items=None):
    """Mengunggah pesan dan file gambar ke Discord Webhook dalam target thread."""
    if THREAD_ID:
        separator = "&" if "?" in WEBHOOK_URL else "?"
        url = f"{WEBHOOK_URL}{separator}thread_id={THREAD_ID}"
    else:
        url = WEBHOOK_URL

    payload = {}
    if content:
        payload["content"] = content

    data = {"payload_json": json.dumps(payload)} if payload else {}
    files = {}

    if file_items:
        for idx, (filename, file_bytes) in enumerate(file_items):
            files[f"files[{idx}]"] = (filename, file_bytes, "image/jpeg")

    try:
        response = requests.post(url, data=data, files=files if files else None, timeout=30)
        if response.status_code in [200, 204]:
            return True
        elif response.status_code == 429:
            retry_after = response.json().get("retry_after", 3)
            print(f"  [!] Rate limit Discord, menunggu {retry_after} detik...")
            time.sleep(retry_after)
            return send_to_discord(content, file_items)
        else:
            print(f"  [-] Discord merespons kode: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"  [-] Gagal mengirim ke Discord: {e}")
        return False


def main():
    print("=" * 60)
    print("🚀 NOGIZAKA COLORS (GEN 6) -> DISCORD UPLOADER (CANVAS PROTOTYPE)")
    print("=" * 60)
    print(f"Target Thread ID: {THREAD_ID}\n")

    if not WEBHOOK_URL or "your_webhook_token_here" in WEBHOOK_URL:
        print("[-] Error: Webhook URL belum dikonfigurasi. Atur DISCORD_WEBHOOK_URL terlebih dahulu.")
        return

    for i, m in enumerate(MEMBERS, 1):
        name_title = f"{m['kanji']} ({m['romaji']})"
        print(f"\n[{i}/{len(MEMBERS)}] Memproses: {name_title} [ID: {m['id']}]")

        photos = get_member_photos(m["id"])
        total_photos = len(photos)
        print(f"  [✓] Ditemukan {total_photos} foto.")

        if total_photos == 0:
            continue

        # 1. Kirim pesan pengantar nama member
        header_text = f"## 🌸 {m['kanji']} / {m['romaji']} (Nogizaka Colors)\nTotal foto: {total_photos} foto."
        send_to_discord(content=header_text)
        time.sleep(1.5)

        # 2. Unduh dan kelompokkan maksimal 10 foto per pesan (Batas Discord)
        batch = []
        batch_num = 1

        for idx, p_url in enumerate(photos, 1):
            try:
                img_resp = requests.get(p_url, headers=HEADERS, timeout=15)
                if img_resp.status_code == 200:
                    ext = "png" if ".png" in p_url.lower() else "jpg"
                    fname = f"{m['romaji'].replace(' ', '_')}_{idx:02d}.{ext}"
                    batch.append((fname, img_resp.content))
            except Exception as e:
                print(f"  [-] Gagal download foto {idx}: {e}")

            # Jika batch sudah mencapai 10 foto atau foto terakhir
            if len(batch) == 10 or idx == total_photos:
                if batch:
                    print(f"  [↑] Mengunggah batch {batch_num} ({len(batch)} foto) ke Discord...")
                    send_to_discord(file_items=batch)
                    batch = []
                    batch_num += 1
                    time.sleep(2.0)  # Jeda aman rate limit Discord

        print(f"  [✓] Selesai untuk {m['romaji']}.")
        time.sleep(2.0)

    print("\n" + "=" * 60)
    print("✨ Seluruh 11 member Generasi ke-6 berhasil diunggah ke Discord!")
    print("=" * 60)


if __name__ == "__main__":
    main()
