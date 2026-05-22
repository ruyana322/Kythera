<div align="center">

```
  __ __     __  __                   
 / //_/_ __/ /_/ /  ___ _______ _    
/ ,< / // / __/ _ \/ -_) __/ _ `/    
/_/|_|\_, /\__/_//_/\__/_/  \_,_/     
      /___/   [ C O R E ]              
                                     
         ✧ by kythera ✧
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
| 1 | **Scan MP4 Structure** | Membaca dan menampilkan hierarki atom/box dalam file MP4 |
| 2 | **Detect moov / mvhd** | Mendeteksi keberadaan dan posisi atom `moov` dan `mvhd` |
| 3 | **Repair Missing moov** | Mencoba memperbaiki file MP4 dengan atom `moov` yang hilang atau rusak |
| 4 | **Patch mvhd Byte** ⭐ | Patch byte spesifik dalam header `mvhd` — fungsi utama toolkit ini |
| 5 | **Analyze Metadata** | Mengekstrak dan menampilkan metadata lengkap dari file MP4 |
| 6 | **Faststart Optimizer** | Memindahkan atom `moov` ke awal file untuk streaming optimal |
| 7 | **Check Corruption** | Memeriksa integritas struktur file dan mendeteksi kerusakan |
| 8 | **Export Scan Report** | Mengekspor hasil scan ke file laporan |

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
# Clone repo
git clone https://github.com/ruyana322/Kythera.git
cd Kythera

# Beri permission
chmod +x kythera.sh

# Jalankan
bash kythera.sh
```

---

## Usage

Setelah dijalankan, pilih menu dengan angka `[1–8]`:

```
  __ __     __  __                   
 / //_/_ __/ /_/ /  ___ _______ _    
/ ,< / // / __/ _ \/ -_) __/ _ `/    
/_/|_|\_, /\__/_//_/\__/_/  \_,_/     
      /___/   [ C O R E ]              
                                     
         ✧ by kythera ✧

╭─────────────────────────────────────────╮
│                                         │
│  [1] Scan MP4 Structure                 │
│  [2] Detect moov/mvhd                   │
│  [3] Repair Missing moov                │
│  [4] Patch mvhd Byte  ★ FUNGSI UTAMA   │
│  [5] Analyze Metadata                   │
│  [6] Faststart Optimizer                │
│  [7] Check Corruption                   │
│  [8] Export Scan Report                 │
│                                         │
│  [0] Exit System                        │
│                                         │
╰─────────────────────────────────────────╯

> Select module (0-8): _
```

Input path file bisa dengan **drag & drop** langsung ke terminal Termux.

### Catatan Penting

- **Menu [4] Patch mvhd Byte** — otomatis membuat backup `.bak` sebelum modifikasi. Pastikan file tidak sedang digunakan proses lain.
- **Menu [6] Faststart Optimizer** — output disimpan sebagai file baru `*_faststart.mp4`. File asli tidak akan diubah.

---

## File Structure

```
Kythera/
├── kythera.sh    # Bash UI wrapper & launcher
├── core.py       # Python engine — logika utama semua fitur
└── README.md
```

---

## How It Works

```
kythera.sh  ──►  UI / Menu Handler
                      │
                      ▼
               core.py [menu_number] [filepath]
                      │
                      ▼
            Binary analysis / patching
            pada struktur MP4 (atom-level)
```

`kythera.sh` bertindak sebagai wrapper UI, lalu memanggil `core.py` dengan argumen nomor menu dan path file. Semua logika biner dihandle oleh Python core.

---

## Author

Made with 🖤 by **kythera**

---

<div align="center">
<sub>Gunakan dengan bijak. Tool ini beroperasi langsung pada binary file.</sub>
</div>
