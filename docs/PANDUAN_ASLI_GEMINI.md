# 📜 Catatan Historis & Panduan Awal (Gemini Canvas)

Dokumen ini mendokumentasikan instruksi awal dan dialog teknis yang dihasilkan pada sesi eksplorasi pertama menggunakan antarmuka **Gemini Web & Canvas**, sebelum sistem disempurnakan menjadi repositori modular modern.

---

## 1. Konteks Awal: Mengapa Harus Dijalankan di Komputer Lokal?

Saat eksplorasi pertama dilakukan, muncul pertanyaan mendasar: *mengapa asisten AI tidak bisa langsung mengunggah foto ke Discord dari dalam antarmuka obrolan?*

### Prinsip Keamanan & Isolasi Cloud (Sandbox):
* **Koneksi Jaringan Keluar Terisolasi**: Sistem asisten AI beroperasi di dalam server yang terisolasi (*sandbox*) tanpa izin akses keluar langsung (*outbound network access*) ke internet publik pihak ketiga demi kepatuhan privasi data dan proteksi keamanan infrastruktur. Oleh karena itu, server AI tidak dapat melakukan `POST` request langsung ke Discord Webhook milik pengguna.
* **Peran Komputer Lokal Pengguna**: Komputer pengguna memiliki koneksi internet langsung ke situs publik [Nogizaka Colors](https://www.nogizaka46.com/s/n46/page/nogizaka_colors) dan API Discord. Webhook yang dibuat (`Captain Hook`) berfungsi sebagai pintu masuk resmi untuk menerima berkas ke thread `Nogizaka Colors (Gen 6)`. Komputer pengguna bertindak sebagai penghubung (*bridge*) yang mengalirkan data secara aman.

---

## 2. Panduan Eksekusi Awal Versi Gemini Canvas

Berikut adalah panduan praktis yang diberikan saat implementasi prototipe pertama kali:

### Komponen Kerja:
* **Python**: Mesin penggerak di komputer lokal untuk mengeksekusi instruksi kerja.
* **`requests`**: Pustaka kurir jaringan yang bertugas mengambil foto dari galeri Nogizaka46 dan mengantarkannya ke Discord Webhook.
* **`beautifulsoup4`**: Pustaka pembaca HTML yang bertugas memisahkan tautan foto member dari tombol navigasi atau logo situs.

### Langkah Eksekusi di Windows (Versi Awal):
1. **Pastikan Python Aktif**:
   * Buka Start Menu, cari `PowerShell` atau `cmd`, lalu tekan **Enter**.
   * Ketik `python --version` untuk memastikan Python sudah terpasang.
2. **Pasang Library Pembantu (Hanya Sekali)**:
   ```bash
   pip install requests beautifulsoup4
   ```
3. **Jalankan Skrip**:
   ```bash
   python nogizaka_uploader.py
   ```

---

## 3. Evaluasi & Pembelajaran dari Versi Prototipe

Meskipun skrip awal berhasil memberikan gambaran solusi, evaluasi langsung menemukan beberapa kendala praktis di lapangan:

1. **Kendala Dependensi Eksternal**: Pengguna awam sering kali mengalami kendala saat menjalankan `pip install beautifulsoup4` (misalnya karena *Path environment variable* belum terkonfigurasi, atau pembatasan hak akses).
   * **Solusi**: Diperbarui menjadi `html.parser` bawaan Python murni (*zero external HTML dependencies*).
2. **Kendala Payload 413 (Payload Too Large)**: Pengelompokan statis 10 foto per pesan sering kali menembus batas kuota 8 MB upload Discord gratis, terutama saat member memiliki foto beresolusi sangat tinggi (seperti foto outdoor atau gaun detail).
   * **Solusi**: Diterapkan *Dynamic Smart Batching* (< 8.5 MB, maksimal 6 foto) dan *Recursive Auto-Split*.
3. **Residu Berkas Sementara**: Menulis file ke folder unduhan lokal dapat menghabiskan ratusan megabyte ruang disk pengguna.
   * **Solusi**: Beralih sepenuhnya ke *in-memory streaming* (data gambar ditampung sementara di RAM dan langsung dibebaskan setelah terkirim).
