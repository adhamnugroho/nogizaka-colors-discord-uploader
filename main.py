#!/usr/bin/env python3
"""Main entrypoint for Nogizaka Colors Discord Uploader.

Scrapes high-resolution official galleries of Nogizaka46 6th Generation members
and uploads them cleanly to a Discord thread via Webhooks.
"""

import argparse
import os
import sys
import time

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from src.config import (
    DEFAULT_RATE_LIMIT_DELAY,
    DISCORD_THREAD_ID,
    DISCORD_WEBHOOK_URL,
    GALLERY_URL_TEMPLATE,
    MAX_BATCH_BYTES,
    MAX_BATCH_FILES,
    MEMBERS,
    validate_config,
)
from src.discord_client import DiscordWebhookClient
from src.scraper import download_image, get_member_photos


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Scrape official Nogizaka Colors galleries and archive them to Discord."
    )
    parser.add_argument(
        "--webhook-url",
        type=str,
        default=None,
        help="Discord Webhook URL (overrides DISCORD_WEBHOOK_URL from .env)",
    )
    parser.add_argument(
        "--thread-id",
        type=str,
        default=None,
        help="Discord Thread ID (overrides DISCORD_THREAD_ID from .env)",
    )
    parser.add_argument(
        "--member-id",
        type=str,
        default=None,
        help="Specific member ID to process (e.g. 63110 for Urumi Morihira)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape galleries and verify image counts without uploading to Discord",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_RATE_LIMIT_DELAY,
        help=f"Delay in seconds between Discord batch uploads (default: {DEFAULT_RATE_LIMIT_DELAY})",
    )
    return parser.parse_args()


def run_pipeline() -> int:
    """Execute the scraping and archiving pipeline."""
    args = parse_arguments()

    webhook_url = args.webhook_url or DISCORD_WEBHOOK_URL
    thread_id = args.thread_id or DISCORD_THREAD_ID
    is_dry_run = args.dry_run

    print("=" * 68)
    print("🌸 NOGIZAKA COLORS (GEN 6) -> DISCORD UPLOADER PIPELINE")
    print("=" * 68)

    # Determine members to process
    if args.member_id:
        target_id = args.member_id.strip()
        selected_members = [m for m in MEMBERS if m["id"] == target_id]
        if not selected_members:
            print(f"[-] Error: Member ID '{target_id}' tidak ditemukan dalam daftar 11 member Gen 6.")
            return 1
    else:
        selected_members = MEMBERS

    if is_dry_run:
        print("🔍 MODE: DRY-RUN AKTIF (Pengikisan & validasi web tanpa upload ke Discord)")
    else:
        if not validate_config(webhook_url):
            print("[-] Error: Webhook Discord belum dikonfigurasi atau tidak valid!")
            print("    Silakan buat berkas .env dari template .env.example atau gunakan opsi --dry-run:")
            print("      cp .env.example .env")
            print("      python main.py --dry-run")
            return 1
        print(f"📡 Target Webhook : {webhook_url[:40]}... (disamarkan)")
        print(f"🧵 Target Thread  : {thread_id or 'Channel Utama (Tanpa Thread)'}")

    print(f"👥 Total Member   : {len(selected_members)} Orang\n")

    client = DiscordWebhookClient(webhook_url=webhook_url, thread_id=thread_id) if not is_dry_run else None

    total_scraped_photos = 0
    total_uploaded_photos = 0
    has_errors = False
    start_time = time.time()

    for idx, member in enumerate(selected_members, 1):
        member_name = f"{member['kanji']} ({member['romaji']})"
        member_id = member["id"]
        source_url = GALLERY_URL_TEMPLATE.format(member_id=member_id)

        print(f"[{idx}/{len(selected_members)}] Memproses: {member_name} [ID: {member_id}]")
        photos = get_member_photos(member_id=member_id)
        photo_count = len(photos)

        if photo_count == 0:
            print(f"  [-] Tidak ada foto ditemukan pada galeri {member['romaji']}.")
            continue

        print(f"  [✓] Terdeteksi {photo_count} foto resmi di galeri.")
        total_scraped_photos += photo_count

        if is_dry_run:
            print(f"  [i] Dry-run: Lewati pengunduhan dan upload untuk {member['romaji']}.")
            continue

        # 1. Kirim Pesan Header Identitas Member
        header_text = (
            f"## 🌸 {member['kanji']} / {member['romaji']} (Nogizaka Colors)\n"
            f"**Total galeri resmi:** {photo_count} foto\n"
            f"*Sumber: {source_url}*"
        )
        print("  [↑] Mengirim header identitas member...")
        if client:
            header_ok = client.send_message(content=header_text)
            if not header_ok:
                print(f"  [-] Peringatan: Gagal mengirim header untuk {member['romaji']}!")
                has_errors = True
            time.sleep(args.delay)

        # 2. Unduh dan Kirim Foto dalam Smart Batches
        current_batch = []
        current_batch_bytes = 0
        batch_index = 1
        member_uploaded = 0

        for p_idx, p_url in enumerate(photos, 1):
            ext = "png" if ".png" in p_url.lower() else "jpg"
            filename = f"{member['romaji'].replace(' ', '_')}_{p_idx:02d}.{ext}"

            print(f"  [↓] Mengunduh foto {p_idx:02d}/{photo_count:02d} ({filename})...")
            img_bytes = download_image(p_url)

            if not img_bytes:
                print(f"  [-] Gagal mengunduh foto {p_idx:02d}, dilewati.")
                has_errors = True
                continue

            img_size = len(img_bytes)

            # Jika batch sudah mencapai limit files atau batas bytes, kirim batch sebelumnya
            if current_batch and (
                len(current_batch) >= MAX_BATCH_FILES or (current_batch_bytes + img_size) > MAX_BATCH_BYTES
            ):
                batch_mb = current_batch_bytes / (1024 * 1024)
                print(f"  [↑] Mengunggah Batch {batch_index} ({len(current_batch)} foto, {batch_mb:.2f} MB)...")
                if client:
                    batch_ok = client.send_message(file_items=current_batch)
                    if batch_ok:
                        member_uploaded += len(current_batch)
                        total_uploaded_photos += len(current_batch)
                    else:
                        print(f"  [-] Gagal mengunggah Batch {batch_index} ({len(current_batch)} foto) ke Discord!")
                        has_errors = True
                    batch_index += 1
                    current_batch = []
                    current_batch_bytes = 0
                    time.sleep(args.delay)

            current_batch.append((filename, img_bytes))
            current_batch_bytes += img_size

        # Kirim sisa foto di batch terakhir
        if current_batch and client:
            batch_mb = current_batch_bytes / (1024 * 1024)
            print(f"  [↑] Mengunggah Batch {batch_index} ({len(current_batch)} foto, {batch_mb:.2f} MB)...")
            batch_ok = client.send_message(file_items=current_batch)
            if batch_ok:
                member_uploaded += len(current_batch)
                total_uploaded_photos += len(current_batch)
            else:
                print(f"  [-] Gagal mengunggah Batch {batch_index} ({len(current_batch)} foto) ke Discord!")
                has_errors = True
            time.sleep(args.delay)

        if member_uploaded == photo_count:
            print(f"  [✓] Sukses mengarsipkan seluruh galeri {member['romaji']}!")
        else:
            print(f"  [!] Arsip {member['romaji']} parsial: {member_uploaded}/{photo_count} terunggah.")
        time.sleep(1.0)

    elapsed = time.time() - start_time
    print("\n" + "=" * 68)
    if is_dry_run:
        print("🎉 VALIDASI DRY-RUN SELESAI!")
        print(f"📊 Total foto terdeteksi di situs resmi: {total_scraped_photos} foto.")
    else:
        if has_errors:
            print("⚠️ ARSIP SELESAI DENGAN CATATAN KENDALA!")
            print(f"📊 Total {total_uploaded_photos} foto berhasil diunggah (beberapa item gagal).")
        else:
            print("🎉 ARSIP LENGKAP SELESAI 100% SUKSES!")
            print(f"📊 Total {total_uploaded_photos} foto berhasil diunggah ke Discord.")
    print(f"⏱ Waktu pengerjaan: {elapsed:.1f} detik ({elapsed/60:.1f} menit).")
    print("=" * 68)
    return 1 if (has_errors and not is_dry_run) else 0


if __name__ == "__main__":
    sys.exit(run_pipeline())
