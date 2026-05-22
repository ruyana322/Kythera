<div align="center">

```
kythera-core v2.1.0
```

**MP4 Binary Structure & Metadata Toolkit**  
*Hex Manipulation · Repair · Faststart*

![Shell](https://img.shields.io/badge/Shell-Bash-4EAA25?style=flat-square&logo=gnubash&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Termux-black?style=flat-square&logo=android&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-cyan?style=flat-square)

</div>

---

## Overview

**Kythera** adalah toolkit berbasis CLI untuk analisis dan manipulasi struktur biner file MP4 langsung dari Termux. Dirancang untuk kebutuhan low-level: mulai dari inspeksi atom box, deteksi metadata, hingga patching byte `mvhd` secara presisi.

---

## Features

| # | Fitur | Deskripsi |
|---|-------|-----------|
| 1 | **Scan structure** | Membaca dan menampilkan hierarki atom/box dalam file MP4 |
| 2 | **Detect moov/mvhd** | Mendeteksi keberadaan dan posisi atom `moov` dan `mvhd` |
| 3 | **Repair moov** | Mencoba memperbaiki file MP4 dengan atom `moov` yang hilang atau rusak |
| 4 | **Patch mvhd byte** ⭐ | Patch byte spesifik dalam header `mvhd` — fungsi utama toolkit ini |
| 5 | **Analyze metadata** | Mengekstrak dan menampilkan metadata lengkap dari file MP4 |
| 6 | **Faststart optimizer** | Memindahkan atom `moov` ke awal file untuk streaming optimal |
| 7 | **Check corruption** | Memeriksa integritas struktur file dan mendeteksi kerusakan |
| 8 | **Export report** | Mengekspor hasil scan ke file laporan |

---

## Requirements

- [Termux](https://termux.dev) (Android)
- Python 3.x
- Bash

Install dependensi:
```bash
pkg update && pkg install python
```

---

## Installation

```bash
git clone https://github.com/ruyana322/Kythera.git
cd Kythera
chmod +x kythera.sh
bash kythera.sh
```

---

## Usage

Saat pertama dijalankan, file browser otomatis terbuka untuk memilih file MP4:

```
 kythera-core / file browser
 ───────────────────────────────────────────────────────────

 location: /storage/emulated/0

  1  DCIM/
  2  Download/
  3  Movies/
  4  broken.mp4   12M

 ───────────────────────────────────────────────────────────
 ketik nomor untuk pilih, atau:
  p  masukkan path manual
  s  storage Android (/storage/emulated/0)
  h  home Termux (~)
  0  batal / kembali

 ───────────────────────────────────────────────────────────
 >
```

Setelah file dipilih, main menu muncul dengan info status file:

```
 kythera-core v2.1.0
 ───────────────────────────────────────────────────────────

 session: 2026-05-22 12:20:14
 target:   broken.mp4  12M
 status:   ⚠  moov atom not found

 ───────────────────────────────────────────────────────────

  1  Scan structure
  2  Detect moov/mvhd
  3  Repair moov
  4  Patch mvhd byte              [primary]
  5  Analyze metadata
  6  Faststart optimizer
  7  Check corruption
  8  Export report

  f  change file
  0  exit

 ───────────────────────────────────────────────────────────
 >
```

### Catatan

- **[4] Patch mvhd byte** — auto-backup `.bak` dibuat sebelum modifikasi
- **[6] Faststart optimizer** — output disimpan sebagai `*_faststart.mp4`, file asli tidak diubah
- **[f]** — ganti file tanpa perlu restart tool
- Status file (`✓ OK` / `⚠ moov not found` / `✗ corrupted`) otomatis update setiap selesai proses

---

## File Structure

```
Kythera/
├── kythera.sh    # bash UI wrapper, file browser & launcher
├── core.py       # python engine — logika utama semua fitur
└── README.md
```

---

## How It Works

```
kythera.sh
    │
    ├── file browser  →  pilih file MP4
    │
    └── main menu  →  core.py [menu_number] [filepath]
                           │
                           └── binary analysis / patching
                               pada struktur MP4 (atom-level)
```

---

## Author

Made with 🖤 by **kythera**

---

<div align="center">
<sub>Gunakan dengan bijak. Tool ini beroperasi langsung pada binary file.</sub>
</div>
