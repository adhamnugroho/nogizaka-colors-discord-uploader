# 🏗️ Technical Architecture & Engineering Decisions

Dokumen ini menjelaskan arsitektur sistem, batasan protokol Discord Webhook, strategi mitigasi kegagalan jaringan, dan komparasi keputusan rekayasa yang diterapkan pada repositori **`nogizaka-colors-discord-uploader`**.

---

## 1. Diagram Alur Sistem (End-to-End Pipeline)

```mermaid
flowchart TD
    A[Situs Resmi Nogizaka Colors\nngColors_{member_id}] -->|GET HTML Request| B[HTML Parser Engine\nhtml.parser bawaan Python]
    B -->|Filter: /images/46/ \nExcl: logos, icons, OGP| C[Daftar URL Foto Resolusi Tinggi]
    C -->|GET Image Bytes| D[In-Memory Streamer\nBuffer RAM tanpa residu disk]
    D --> E{Dynamic Smart Batcher\nMax 6 Foto ATAU < 8.5 MB?}
    E -->|Kapasitas Batch Penuh| F[Discord Webhook Client\nMultipart Form-Data]
    E -->|Masih Muat| D
    F --> G{Status Kode Discord}
    G -->|200 / 204 OK| H[Pesan & Grid Foto Tampil\ndi Thread Discord]
    G -->|429 Rate Limit| I[Adaptive Backoff\nSleep retry_after + 0.5s]
    I --> F
    G -->|413 Payload Too Large| J[Auto-Split Bisector\nPecah Batch jadi 2 Bagian]
    J --> F
```

---

## 2. Bedah Komparasi Rekayasa: Prototype vs Robust Engine

Perancangan repositori ini merupakan hasil evolusi dari purwarupa awal (*Gemini Canvas*) menuju *Production-Ready Engine*:

| Aspek Teknis | Purwarupa Awal (`scripts/original_canvas_script.py`) | Engine Robust (`src/` & `standalone_uploader.py`) | Alasan Keputusan Rekayasa |
|:---|:---|:---|:---|
| **Dependensi HTML** | Memerlukan `beautifulsoup4` eksternal. | **Zero External Dependencies** (`html.parser` standar). | Memungkinkan skrip dijalankan di komputer mana pun tanpa instalasi paket rumit atau hak administrator. |
| **Penyimpanan Berkas** | Berpotensi meninggalkan file sementara di disk lokal. | **100% In-Memory Streaming** via `bytes` buffer. | Mencegah penumpukan sampah disk ratusan MB (~220 MB untuk 11 member). |
| **Metode Batching** | Statis 10 foto per pesan (mengabaikan ukuran total). | **Dynamic Smart Batching** (Maks 6 foto ATAU < 8.5 MB). | Menjamin payload tetap di bawah ambang batas upload Discord gratis (~8 MB/10 MB). |
| **Penanganan HTTP 413** | Fatal error / pesan gagal terkirim selamanya. | **Recursive Bisect Fallback** (Membagi batch menjadi 2). | Jika foto beresolusi sangat besar menyentuh limit, sistem otomatis memecahnya tanpa intervensi pengguna. |
| **Penanganan HTTP 429** | Pemanggilan fungsi rekursif tanpa batasan (*stack overflow risk*). | **Linear Retries Loop** dengan pembacaan presisi `retry_after`. | Mencegah crash memory dan mematuhi aturan laju request Discord secara elegan. |
| **Routing Thread** | Hardcoded di dalam string skrip. | **Modular Configuration** (`.env` / query param builder). | Memisahkan kredensial dan target thread secara aman sesuai prinsip *12-Factor App*. |

---

## 3. Protokol & Spesifikasi Discord Webhook API

### A. Pengiriman ke Discord Thread
Secara default, webhook Discord mengirim pesan ke channel induk (*parent channel*). Agar pesan masuk ke dalam Thread tertentu (misal thread `Nogizaka Colors (Gen 6)`), Discord API menyediakan query parameter:

```http
POST https://discord.com/api/webhooks/{webhook.id}/{webhook.token}?thread_id={thread_id}
Content-Type: multipart/form-data
```

Klien di repositori ini secara otomatis menambahkan query parameter `?thread_id=` jika `DISCORD_THREAD_ID` diisi, atau menggunakan channel utama jika dikosongkan.

### B. Struktur Multipart Form-Data
Pengiriman teks pengantar dan kumpulan file foto dikemas dalam satu transaksi HTTP multipart:
- **`payload_json`**: String JSON yang memuat konten Markdown header identitas member.
- **`files[0]`, `files[1]`, ... `files[N]`**: File binary gambar dengan MIME type `image/jpeg` atau `image/png`.

Discord secara otomatis merender berkas multi-image menjadi **grid preview interaktif** jika dikirim dalam satu pesan yang sama.

### C. Manajemen Rate Limiting (HTTP 429)
Discord menerapkan *bucket-based rate limiting*. Ketika batas request tercapai, Discord merespons dengan kode `429 Too Many Requests` dan mengembalikan payload JSON:

```json
{
  "message": "You are being rate limited.",
  "retry_after": 2.5,
  "global": false
}
```

Klien membaca field `retry_after`, menambahkan *safety margin* sebesar 0.5 detik, lalu melakukan jeda eksekusi sebelum mengulang pengiriman.

### D. Manajemen Payload Too Large (HTTP 413)
Server Discord memiliki batas maksimum ukuran payload per pesan (8 MB untuk server biasa, 25-50 MB untuk server tier boost). 
Ketika batch berisi foto beresolusi sangat tinggi melebihi kuota upload:
1. Server Discord membalas dengan status `HTTP 413 Request Entity Too Large`.
2. Fungsi `send_to_discord` menangkap status tersebut.
3. Batch berisi $N$ file langsung dipecah (*bisection*) menjadi dua sub-batch:
   $$\text{Part}_1 = \text{files}[0 \dots \lfloor N/2 \rfloor], \quad \text{Part}_2 = \text{files}[\lfloor N/2 \rfloor \dots N]$$
4. Masing-masing sub-batch dikirim secara terpisah dengan jeda 2 detik.

---

## 4. Keamanan Kredensial & Lingkungan

1. **Prinsip Zero-Leakage**: Kredensial Webhook bersifat rahasia karena siapa pun yang memegang URL webhook dapat mengirimkan pesan ke server Discord Anda tanpa autentikasi login.
2. **Template Lingkungan**: Seluruh kode produksi hanya membaca dari environment variable (`DISCORD_WEBHOOK_URL`). Berkas `.env.example` disediakan dengan string dummy.
3. **Penyaringan Git**: Berkas `.gitignore` secara permanen mengabaikan `.env`, `*.env`, dan folder `downloads/`.

---

## 5. Strategi Pengujian Otomatis (Automated Testing Strategy)

Untuk mencegah regresi dan memvalidasi keandalan komponen inti tanpa melakukan panggilan jaringan eksternal yang tidak perlu ke Discord, repositori menyediakan suite unit test mandiri berbasis pustaka standar `unittest` (`tests/`):

- **`test_config.py`**: Memvalidasi integritas 11 anggota Generasi ke-6 (keabsahan ID, Kanji, dan Romaji resmi) serta aturan validasi URL webhook dummy vs asli.
- **`test_scraper.py`**: Menguji ketepatan penyaringan URL gambar beresolusi tinggi pada pola `/images/46/`, eliminasi aset chrome (logo/ikon/ogp), penanganan atribut lazy-load `data-src`, dan konversi URL relatif ke absolut.
- **`test_discord_client.py`**: Menguji pembentukan query parameter thread Discord (`?thread_id=` dan `&thread_id=`), proteksi payload kosong, pemetaan MIME type multi-format (`.png`, `.jpg`, `.webp`, `.gif`), simulasi pemulihan HTTP 429 rate limit backoff, serta pembagian bisection HTTP 413 dengan pelestarian konten pesan.
- **`test_cli.py`**: Memvalidasi parser argumen baris perintah (`main.py`) serta kode keluar (*exit codes*) saat terjadi galat masukan atau mode dry-run.
