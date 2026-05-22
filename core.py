#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════╗
# ║   KYTHERA CORE — core.py                                    ║
# ║   Python Binary Manipulation Engine                         ║
# ║   MP4 Box Parser · mvhd Patcher · Faststart Optimizer       ║
# ╚══════════════════════════════════════════════════════════════╝

import sys
import os
import struct
import shutil
import json
import hashlib
from datetime import datetime

# ── ANSI COLORS ───────────────────────────────────────────────
CYAN   = '\033[96m'
WHITE  = '\033[97m'
YELLOW = '\033[93m'
RED    = '\033[91m'
GREEN  = '\033[92m'
GRAY   = '\033[90m'
BOLD   = '\033[1m'
RESET  = '\033[0m'

def pi(msg):   print(f"  {CYAN}[*]{RESET} {msg}")
def pok(msg):  print(f"  {GREEN}[✓]{RESET} {msg}")
def pw(msg):   print(f"  {YELLOW}[!]{RESET} {msg}")
def perr(msg): print(f"  {RED}[✗]{RESET} {msg}", file=sys.stderr)

def section(title):
    bar = '─' * 52
    print(f"\n{CYAN}  ╔{bar}╗{RESET}")
    pad = (52 - len(title)) // 2
    print(f"{CYAN}  ║{RESET}{' '*pad}{BOLD}{WHITE}{title}{RESET}{' '*(52-pad-len(title))}{CYAN}║{RESET}")
    print(f"{CYAN}  ╚{bar}╝{RESET}\n")


# ══════════════════════════════════════════════════════════════
#  MP4Box — representasi satu box/atom MP4
# ══════════════════════════════════════════════════════════════
class MP4Box:
    __slots__ = ('size', 'type', 'offset', 'data')

    def __init__(self, size, box_type, offset, data):
        self.size   = size
        self.type   = box_type
        self.offset = offset
        self.data   = data

    def __repr__(self):
        return f"MP4Box(type={self.type!r}, size={self.size}, offset={self.offset})"


# ══════════════════════════════════════════════════════════════
#  KytheraCoreEngine — mesin utama
# ══════════════════════════════════════════════════════════════
class KytheraCoreEngine:

    def __init__(self, filepath: str):
        self.filepath    = filepath
        self.backup_path = filepath + '.bak'

    # ── Internal: validasi file ───────────────────────────────
    def _validate(self) -> bool:
        if not os.path.exists(self.filepath):
            perr(f"File tidak ditemukan: {self.filepath}")
            return False
        if os.path.getsize(self.filepath) < 8:
            perr("File terlalu kecil — bukan MP4 valid.")
            return False
        if not self.filepath.lower().endswith('.mp4'):
            pw("Ekstensi bukan .mp4 — tetap dilanjutkan.")
        return True

    # ── Internal: baca seluruh file ke bytes ──────────────────
    def _read_file(self) -> bytes | None:
        try:
            with open(self.filepath, 'rb') as f:
                return f.read()
        except Exception as e:
            perr(f"Gagal membaca file: {e}")
            return None

    # ── Internal: auto-backup sebelum modifikasi ──────────────
    def _backup(self) -> bool:
        if os.path.exists(self.backup_path):
            pw(f"Backup sudah ada: {os.path.basename(self.backup_path)}")
            return True
        try:
            shutil.copy2(self.filepath, self.backup_path)
            pok(f"Auto-backup tersimpan → {os.path.basename(self.backup_path)}")
            return True
        except Exception as e:
            perr(f"Gagal membuat backup: {e}")
            return False

    # ── Internal: parse linear box list dari binary data ──────
    def _parse_boxes(self, data: bytes, base_offset: int = 0) -> list[MP4Box]:
        boxes = []
        pos   = 0
        end   = len(data)

        while pos + 8 <= end:
            try:
                raw_size = struct.unpack('>I', data[pos:pos+4])[0]
                box_type = data[pos+4:pos+8].decode('latin-1')

                if raw_size == 1:
                    # Extended 64-bit size
                    if pos + 16 > end:
                        break
                    size = struct.unpack('>Q', data[pos+8:pos+16])[0]
                elif raw_size == 0:
                    # Extends to end of parent
                    size = end - pos
                else:
                    size = raw_size

                if size < 8 or pos + size > end + 4:
                    pos += 1
                    continue

                boxes.append(MP4Box(
                    size       = size,
                    box_type   = box_type,
                    offset     = base_offset + pos,
                    data       = data[pos : pos + size],
                ))
                pos += size

            except Exception:
                pos += 1

        return boxes

    # ── Internal: patch stco/co64 offset tables ───────────────
    def _patch_chunk_offsets(self, moov_data: bytes, shift: int) -> bytes:
        buf = bytearray(moov_data)
        pos = 0

        while pos + 8 <= len(buf):
            if pos + 4 > len(buf):
                break
            raw_size = struct.unpack('>I', buf[pos:pos+4])[0]
            if raw_size < 8:
                pos += 1
                continue
            box_type = bytes(buf[pos+4:pos+8])

            if box_type == b'stco':
                ec_off = pos + 12
                if ec_off + 4 > len(buf):
                    break
                ec = struct.unpack('>I', buf[ec_off:ec_off+4])[0]
                pi(f"  Patching stco — {ec} chunk entries (shift +{shift})")
                for i in range(ec):
                    ep = ec_off + 4 + i * 4
                    if ep + 4 > len(buf):
                        break
                    old = struct.unpack('>I', buf[ep:ep+4])[0]
                    struct.pack_into('>I', buf, ep, old + shift)

            elif box_type == b'co64':
                ec_off = pos + 12
                if ec_off + 4 > len(buf):
                    break
                ec = struct.unpack('>I', buf[ec_off:ec_off+4])[0]
                pi(f"  Patching co64 — {ec} chunk entries (shift +{shift})")
                for i in range(ec):
                    ep = ec_off + 4 + i * 8
                    if ep + 8 > len(buf):
                        break
                    old = struct.unpack('>Q', buf[ep:ep+8])[0]
                    struct.pack_into('>Q', buf, ep, old + shift)

            pos += raw_size

        return bytes(buf)

    # ── Internal: parse mvhd fields (version 0 & 1) ───────────
    def _parse_mvhd(self, mvhd_payload: bytes) -> dict:
        """mvhd_payload = bytes setelah string 'mvhd' (4 bytes)"""
        if len(mvhd_payload) < 4:
            return {}
        version = mvhd_payload[0]
        result  = {'version': version}

        if version == 0 and len(mvhd_payload) >= 100:
            result['timescale']  = struct.unpack('>I', mvhd_payload[12:16])[0]
            result['duration']   = struct.unpack('>I', mvhd_payload[16:20])[0]
            result['rate_raw']   = struct.unpack('>I', mvhd_payload[20:24])[0]
            result['vol_raw']    = struct.unpack('>H', mvhd_payload[24:26])[0]
            result['next_track'] = struct.unpack('>I', mvhd_payload[96:100])[0]
            result['byte_44']    = mvhd_payload[44]
        elif version == 1 and len(mvhd_payload) >= 112:
            result['timescale']  = struct.unpack('>I', mvhd_payload[20:24])[0]
            result['duration']   = struct.unpack('>Q', mvhd_payload[24:32])[0]
            result['rate_raw']   = struct.unpack('>I', mvhd_payload[32:36])[0]
            result['vol_raw']    = struct.unpack('>H', mvhd_payload[36:38])[0]
            result['next_track'] = struct.unpack('>I', mvhd_payload[108:112])[0]
            result['byte_44']    = mvhd_payload[44]

        if 'timescale' in result and 'duration' in result:
            ts = result['timescale']
            result['duration_sec'] = result['duration'] / ts if ts else 0
            if 'rate_raw' in result:
                result['rate']   = result['rate_raw'] / 0x10000
                result['volume'] = result['vol_raw']  / 0x100

        return result

    # ══════════════════════════════════════════════════════════
    #  MENU 1 — Scan MP4 Structure
    # ══════════════════════════════════════════════════════════
    def scan_structure(self):
        section("SCAN MP4 STRUCTURE")
        if not self._validate():
            return
        data = self._read_file()
        if data is None:
            return

        file_size = len(data)
        pi(f"File : {BOLD}{os.path.basename(self.filepath)}{RESET}")
        pi(f"Size : {file_size:,} bytes  ({file_size/1024/1024:.2f} MB)")

        boxes = self._parse_boxes(data)

        print(f"\n  {CYAN}{'OFFSET':>10}  {'SIZE':>12}  {'TYPE':<6}  INFO{RESET}")
        print(f"  {CYAN}{'─'*10}  {'─'*12}  {'─'*6}  {'─'*28}{RESET}")

        for box in boxes:
            info  = ''
            color = WHITE

            if box.type == 'ftyp':
                color = CYAN
                if len(box.data) >= 12:
                    brand = box.data[8:12].decode('latin-1').rstrip('\x00')
                    info  = f"brand={brand!r}"
            elif box.type == 'mdat':
                info = 'media data payload'
            elif box.type == 'moov':
                color = CYAN
                info  = 'movie container ✓'
                # sub-boxes
                print(f"  {box.offset:>10}  {box.size:>12}  {color}{box.type:<6}{RESET}  {info}")
                sub = self._parse_boxes(box.data[8:], box.offset + 8)
                for sb in sub:
                    sub_info = {
                        'mvhd': 'movie header',
                        'trak': 'track container',
                        'udta': 'user data',
                        'meta': 'metadata',
                        'iods': 'initial object descriptor',
                    }.get(sb.type, '')
                    sc = YELLOW if sb.type == 'mvhd' else GRAY
                    print(f"  {sb.offset:>10}  {sb.size:>12}  {sc}  └─{sb.type:<4}{RESET}  {sub_info}")
                continue
            elif box.type in ('free', 'skip', 'wide'):
                info = 'padding / free space'
            elif box.type == 'uuid':
                info = 'vendor extension'

            print(f"  {box.offset:>10}  {box.size:>12}  {color}{box.type:<6}{RESET}  {info}")

        print(f"\n  {GREEN}Total: {len(boxes)} top-level box(es) ditemukan{RESET}")

    # ══════════════════════════════════════════════════════════
    #  MENU 2 — Detect moov / mvhd
    # ══════════════════════════════════════════════════════════
    def detect_moov_mvhd(self):
        section("DETECT moov / mvhd")
        if not self._validate():
            return
        data = self._read_file()
        if data is None:
            return

        # ─ moov ──────────────────────────────────────────────
        moov_pos = data.find(b'moov')
        mdat_pos = data.find(b'mdat')

        if moov_pos == -1:
            perr("'moov' atom TIDAK ditemukan — file mungkin corrupt atau bukan MP4.")
        else:
            moov_box_offset = moov_pos - 4
            moov_size       = struct.unpack('>I', data[moov_box_offset:moov_pos])[0]
            pok(f"'moov' ditemukan  offset={moov_box_offset}  size={moov_size:,} bytes")

            if mdat_pos != -1:
                if moov_pos < mdat_pos:
                    pok("Posisi moov: SEBELUM mdat → Faststart-ready ✓")
                else:
                    pw("Posisi moov: SETELAH mdat → Tidak web-optimized (gunakan menu [6])")

        print()

        # ─ mvhd ──────────────────────────────────────────────
        mvhd_pos = data.find(b'mvhd')
        if mvhd_pos == -1:
            perr("'mvhd' atom TIDAK ditemukan.")
        else:
            mvhd_box_offset = mvhd_pos - 4
            mvhd_size       = struct.unpack('>I', data[mvhd_box_offset:mvhd_pos])[0]
            pok(f"'mvhd' ditemukan  offset={mvhd_box_offset}  size={mvhd_size} bytes")

            payload = data[mvhd_pos + 4:]   # setelah 4-char 'mvhd'
            info    = self._parse_mvhd(payload)

            if info:
                pi(f"  Version   : {info.get('version')}")
                ts  = info.get('timescale', 0)
                dur = info.get('duration_sec', 0)
                pi(f"  Timescale : {ts} units/sec")
                pi(f"  Duration  : {dur:.3f}s  ({int(dur//60)}m {dur%60:.1f}s)")
                pi(f"  Rate      : {info.get('rate', 0):.4f}x")
                pi(f"  Volume    : {info.get('volume', 0)*100:.0f}%")
                pi(f"  Next Track: {info.get('next_track', '?')}")

            if 'byte_44' in info:
                b44 = info['byte_44']
                print()
                target_offset = mvhd_pos + 4 + 44
                print(f"  {YELLOW}{'━'*48}{RESET}")
                print(f"  {YELLOW}★ Byte ke-44 setelah 'mvhd'{RESET}")
                print(f"    File offset : {target_offset}")
                print(f"    Nilai saat  : {BOLD}0x{b44:02X}{RESET}  ({b44} dec)")
                print(f"  {YELLOW}{'━'*48}{RESET}")

    # ══════════════════════════════════════════════════════════
    #  MENU 3 — Repair Missing moov
    # ══════════════════════════════════════════════════════════
    def repair_missing_moov(self):
        section("REPAIR MISSING moov")
        if not self._validate():
            return
        data = self._read_file()
        if data is None:
            return

        moov_pos = data.find(b'moov')
        if moov_pos != -1:
            pok(f"'moov' sudah ada di offset {moov_pos - 4}. File tidak perlu di-repair.")
            return

        perr("'moov' tidak ditemukan!")
        print()

        # Cek fragmented MP4 (moof)
        moof_pos = data.find(b'moof')
        if moof_pos != -1:
            pw(f"'moof' (fragment) ditemukan di offset {moof_pos - 4}")
            pw("File ini adalah Fragmented MP4 — butuh re-mux, bukan repair biasa.")
            pi("Coba di Termux:")
            print(f"    {CYAN}ffmpeg -i input.mp4 -c copy -movflags faststart output.mp4{RESET}")
            return

        # Cek apakah ada mdat
        mdat_pos = data.find(b'mdat')
        if mdat_pos != -1:
            pw(f"'mdat' ada di offset {mdat_pos - 4} tapi tidak ada 'moov'.")
            pw("File kemungkinan terputus saat recording (crash / baterai habis).")
            pi("Gunakan tool recovery:")
            pi("  • untrunc (butuh file referensi yang sehat)")
            pi("  • mp4recover")
            pi("  • ffmpeg -i input.mp4 -c copy -ignore_unknown output.mp4")
        else:
            perr("Tidak ada mdat maupun moov — file corrupt sangat parah.")
            pi("Pertimbangkan recovery dengan hex editor manual atau tool forensik.")

    # ══════════════════════════════════════════════════════════
    #  MENU 4 — Patch mvhd Byte  ★ FUNGSI UTAMA
    # ══════════════════════════════════════════════════════════

    # ── Helper: tampilkan context hex di sekitar offset ──────
    def _show_context(self, data: bytes, target_abs: int, label: str = ""):
        ctx_s = max(0, target_abs - 6)
        ctx_e = min(len(data), target_abs + 7)
        if label:
            print(f"  {GRAY}Context hex — {label} (offset {ctx_s}–{ctx_e-1}):{RESET}")
        else:
            print(f"  {GRAY}Context hex (offset {ctx_s}–{ctx_e-1}):{RESET}")
        hex_parts = []
        for i, b in enumerate(data[ctx_s:ctx_e]):
            if ctx_s + i == target_abs:
                hex_parts.append(f"{YELLOW}{BOLD}[{b:02X}]{RESET}")
            else:
                hex_parts.append(f"{GRAY}{b:02X}{RESET}")
        print("  " + " ".join(hex_parts))

    # ── Helper: tulis 1 byte ke file ─────────────────────────
    def _write_byte(self, offset: int, new_val: int, current_val: int):
        print()
        print(f"  {YELLOW}{'━'*46}{RESET}")
        print(f"  {YELLOW}KONFIRMASI PATCH:{RESET}")
        print(f"    Offset   : {offset}")
        print(f"    Sebelum  : 0x{current_val:02X}  ({current_val})")
        print(f"    Sesudah  : {BOLD}0x{new_val:02X}  ({new_val}){RESET}")
        print(f"    Backup   : {os.path.basename(self.backup_path)}")
        print(f"  {YELLOW}{'━'*46}{RESET}")
        print()
        print(f"  {RED}Lanjutkan patch? (y/N){RESET}")
        try:
            confirm = input(f"  {YELLOW}» {RESET}").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(f"\n  {YELLOW}Dibatalkan.{RESET}")
            return
        if confirm != 'y':
            pw("Patch dibatalkan.")
            return
        try:
            with open(self.filepath, 'rb+') as f:
                f.seek(offset)
                f.write(bytes([new_val]))
            pok(f"Patch sukses! Offset {offset} → 0x{new_val:02X}")
            pi(f"Backup: {self.backup_path}")
        except PermissionError:
            perr("Permission denied.")
        except Exception as e:
            perr(f"Gagal menulis: {e}")

    # ── Helper: input hex 1 byte ──────────────────────────────
    def _input_hex_byte(self) -> int | None:
        print(f"  {CYAN}Masukkan nilai hex baru (1 byte, contoh: 01  37  FF  00):{RESET}")
        try:
            raw = input(f"  {YELLOW}» {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n  {YELLOW}Dibatalkan.{RESET}")
            return None
        raw = raw.replace('0x', '').replace('0X', '').strip()
        if not raw:
            pw("Tidak ada input.")
            return None
        if len(raw) > 2:
            perr(f"Terlalu panjang — maks 2 karakter hex.")
            return None
        try:
            return int(raw, 16)
        except ValueError:
            perr(f"Input tidak valid: '{raw}'")
            return None

    def patch_mvhd_byte(self):
        section("PATCH mvhd BYTE  ★")
        if not self._validate():
            return
        if not self._backup():
            perr("Patch dibatalkan — backup gagal.")
            return
        data = self._read_file()
        if data is None:
            return

        mvhd_pos = data.find(b'mvhd')
        if mvhd_pos == -1:
            perr("'mvhd' tidak ditemukan.")
            return

        info = self._parse_mvhd(data[mvhd_pos + 4:])
        ver  = info.get('version', 0)

        # ─ Definisi semua field mvhd (version 0) ─────────────
        # offset dihitung dari mvhd_pos (dari huruf 'm')
        if ver == 0:
            fields = [
                (4,  1,  "version",        "versi mvhd (0 atau 1)"),
                (5,  3,  "flags",          "flags (biasanya 00 00 00)"),
                (8,  4,  "creation_time",  "waktu pembuatan (detik sejak 1904)"),
                (12, 4,  "modification_time", "waktu modifikasi"),
                (16, 4,  "timescale",      "unit per detik"),
                (20, 4,  "duration",       "durasi dalam timescale units"),
                (24, 4,  "rate",           "kecepatan putar (0x00010000 = 1.0x)"),
                (28, 2,  "volume",         "volume (0x0100 = 100%)"),
                (30, 10, "reserved",       "reserved bytes"),
                (40, 36, "matrix",         "transformation matrix (9×4 bytes)"),
                (76, 24, "pre_defined",    "pre-defined (biasanya nol)"),
                (100,4,  "next_track_id",  "ID track berikutnya"),
            ]
        else:
            fields = [
                (4,  1,  "version",        "versi mvhd (0 atau 1)"),
                (5,  3,  "flags",          "flags"),
                (8,  8,  "creation_time",  "waktu pembuatan (64-bit)"),
                (16, 8,  "modification_time", "waktu modifikasi (64-bit)"),
                (24, 4,  "timescale",      "unit per detik"),
                (28, 8,  "duration",       "durasi (64-bit)"),
                (36, 4,  "rate",           "kecepatan putar"),
                (40, 2,  "volume",         "volume"),
                (42, 10, "reserved",       "reserved"),
                (52, 36, "matrix",         "transformation matrix"),
                (88, 24, "pre_defined",    "pre-defined"),
                (112,4,  "next_track_id",  "ID track berikutnya"),
            ]

        # ─ SUB MENU ───────────────────────────────────────────
        while True:
            print()
            print(f"  {CYAN}{'─'*52}{RESET}")
            print(f"  {BOLD}{WHITE}PILIH MODE:{RESET}")
            print(f"  {CYAN}{'─'*52}{RESET}")
            print(f"  {WHITE}1{RESET}  {GRAY}Pilih field mvhd (byte selector){RESET}")
            print(f"  {WHITE}2{RESET}  {GRAY}Search string / hex pattern{RESET}")
            print(f"  {WHITE}0{RESET}  {GRAY}Kembali{RESET}")
            print(f"  {CYAN}{'─'*52}{RESET}")
            print()
            try:
                mode = input(f"  {YELLOW}» {RESET}").strip()
            except (KeyboardInterrupt, EOFError):
                return

            if mode == '0':
                return

            elif mode == '1':
                self._patch_field_selector(data, mvhd_pos, fields, ver)
                # Reload data setelah patch
                data = self._read_file()
                if data is None:
                    return

            elif mode == '2':
                self._search_pattern(data)

            else:
                pw("Pilihan tidak valid.")

    # ── Mode 1: Field selector ────────────────────────────────
    def _patch_field_selector(self, data: bytes, mvhd_pos: int, fields: list, ver: int):
        print()
        print(f"  {CYAN}mvhd{RESET} ditemukan di offset {mvhd_pos}  (version {ver})")
        print()
        print(f"  {CYAN}{'NO':<4} {'FIELD':<22} {'OFFSET(abs)':<14} {'SIZE':<6} {'VALUE (hex)'}{RESET}")
        print(f"  {GRAY}{'─'*4} {'─'*22} {'─'*14} {'─'*6} {'─'*20}{RESET}")

        for i, (rel_off, size, name, desc) in enumerate(fields):
            abs_off = mvhd_pos + rel_off
            if abs_off + size <= len(data):
                raw = data[abs_off:abs_off+size]
                hex_val = raw.hex(' ').upper()
                # Singkat kalau panjang
                if len(hex_val) > 20:
                    hex_val = hex_val[:20] + '…'
            else:
                hex_val = '??'
            print(f"  {YELLOW}{i+1:<4}{RESET} {WHITE}{name:<22}{RESET} {GRAY}{abs_off:<14}{RESET} {GRAY}{size:<6}{RESET} {CYAN}{hex_val}{RESET}")
            print(f"  {GRAY}       {desc}{RESET}")

        print()
        print(f"  {GRAY}Ketik nomor field yang mau di-patch, atau 0 untuk batal:{RESET}")
        try:
            sel = input(f"  {YELLOW}» {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            return

        if sel == '0' or not sel:
            return

        try:
            idx = int(sel) - 1
        except ValueError:
            pw("Input tidak valid.")
            return

        if idx < 0 or idx >= len(fields):
            pw("Nomor tidak ada.")
            return

        rel_off, size, name, desc = fields[idx]
        abs_off = mvhd_pos + rel_off

        print()
        pi(f"Field    : {BOLD}{name}{RESET} — {desc}")
        pi(f"Offset   : {abs_off}  (relatif mvhd+{rel_off})")
        pi(f"Size     : {size} byte(s)")

        raw = data[abs_off:abs_off+size]
        print(f"  {GRAY}Nilai saat ini: {CYAN}{raw.hex(' ').upper()}{RESET}")
        print()
        self._show_context(data, abs_off, name)
        print()

        if size == 1:
            new_val = self._input_hex_byte()
            if new_val is None:
                return
            current_val = data[abs_off]
            if new_val == current_val:
                pw("Nilai sama — tidak ada perubahan.")
                return
            self._write_byte(abs_off, new_val, current_val)
        else:
            print(f"  {CYAN}Field ini {size} bytes. Masukkan hex baru ({size} bytes, spasi antar byte):{RESET}")
            print(f"  {GRAY}Contoh untuk {size} bytes: " + ' '.join(['00']*size) + f"{RESET}")
            try:
                raw_in = input(f"  {YELLOW}» {RESET}").strip()
            except (KeyboardInterrupt, EOFError):
                return
            try:
                new_bytes = bytes.fromhex(raw_in.replace(' ', ''))
            except ValueError:
                perr("Format hex tidak valid.")
                return
            if len(new_bytes) != size:
                perr(f"Harus tepat {size} bytes, dapat {len(new_bytes)}.")
                return

            print()
            print(f"  {YELLOW}{'━'*46}{RESET}")
            print(f"  {YELLOW}KONFIRMASI PATCH:{RESET}")
            print(f"    Field    : {name}")
            print(f"    Offset   : {abs_off}")
            print(f"    Sebelum  : {raw.hex(' ').upper()}")
            print(f"    Sesudah  : {BOLD}{new_bytes.hex(' ').upper()}{RESET}")
            print(f"    Backup   : {os.path.basename(self.backup_path)}")
            print(f"  {YELLOW}{'━'*46}{RESET}")
            print()
            print(f"  {RED}Lanjutkan? (y/N){RESET}")
            try:
                confirm = input(f"  {YELLOW}» {RESET}").strip().lower()
            except (KeyboardInterrupt, EOFError):
                return
            if confirm != 'y':
                pw("Dibatalkan.")
                return
            try:
                with open(self.filepath, 'rb+') as f:
                    f.seek(abs_off)
                    f.write(new_bytes)
                pok(f"Patch sukses! {name} @ offset {abs_off} → {new_bytes.hex(' ').upper()}")
            except Exception as e:
                perr(f"Gagal tulis: {e}")

    # ── Mode 2: Search string / hex pattern ──────────────────
    def _search_pattern(self, data: bytes):
        print()
        print(f"  {CYAN}{'─'*52}{RESET}")
        print(f"  {BOLD}{WHITE}SEARCH PATTERN{RESET}")
        print(f"  {CYAN}{'─'*52}{RESET}")
        print(f"  {GRAY}Contoh:{RESET}")
        print(f"  {GRAY}  string : moov  ftyp  mvhd  mdat  trak{RESET}")
        print(f"  {GRAY}  hex    : 00 00 01  atau  0x00 0x01{RESET}")
        print(f"  {GRAY}  mixed  : ketik apa saja, auto-detect{RESET}")
        print()
        try:
            raw_in = input(f"  {YELLOW}» {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            return

        if not raw_in:
            return

        # Auto-detect: coba parse sebagai hex dulu
        pattern = None
        mode_label = ''

        # Cek apakah input terlihat seperti hex (spasi-separated atau 0x prefix)
        cleaned = raw_in.replace('0x', '').replace('0X', '').replace(',', ' ').strip()
        parts   = cleaned.split()
        is_hex  = all(len(p) <= 2 and all(c in '0123456789abcdefABCDEF' for c in p) for p in parts)

        if is_hex and len(parts) > 1:
            try:
                pattern    = bytes.fromhex(''.join(parts))
                mode_label = f"hex [{raw_in}]"
            except ValueError:
                pass

        if pattern is None:
            # Perlakukan sebagai string ASCII / atom name
            try:
                pattern    = raw_in.encode('latin-1')
                mode_label = f"string [{raw_in!r}]"
            except Exception:
                perr("Pattern tidak valid.")
                return

        print()
        pi(f"Mencari {mode_label} di {len(data):,} bytes…")
        print()

        hits = []
        start = 0
        while True:
            pos = data.find(pattern, start)
            if pos == -1:
                break
            hits.append(pos)
            start = pos + 1

        if not hits:
            pw(f"Pattern tidak ditemukan dalam file.")
            return

        pok(f"Ditemukan {len(hits)} hit:")
        print()
        print(f"  {CYAN}{'NO':<5} {'OFFSET (dec)':<16} {'OFFSET (hex)':<14} {'BYTE KE-':<12} CONTEXT{RESET}")
        print(f"  {GRAY}{'─'*5} {'─'*16} {'─'*14} {'─'*12} {'─'*24}{RESET}")

        for i, pos in enumerate(hits[:50]):  # max 50 hits
            # Context: 4 byte sebelum dan 4 byte sesudah
            ctx_s  = max(0, pos - 4)
            ctx_e  = min(len(data), pos + len(pattern) + 4)
            ctx    = data[ctx_s:ctx_e]
            # Build hex context dengan highlight
            ctx_hex = ''
            for j, b in enumerate(ctx):
                abs_j = ctx_s + j
                if pos <= abs_j < pos + len(pattern):
                    ctx_hex += f"[{b:02X}]"
                else:
                    ctx_hex += f"{b:02X} "

            print(f"  {YELLOW}{i+1:<5}{RESET} {WHITE}{pos:<16}{RESET} {CYAN}0x{pos:08X}{RESET}      {GRAY}{pos:<12}{RESET} {GRAY}{ctx_hex[:28]}{RESET}")

        if len(hits) > 50:
            pw(f"Menampilkan 50 dari {len(hits)} hit total.")

        print()
        # Tawaran: mau patch salah satu hit?
        print(f"  {GRAY}Mau patch byte di salah satu offset di atas? (ketik nomor hit / 0 untuk skip){RESET}")
        try:
            sel = input(f"  {YELLOW}» {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            return

        if sel == '0' or not sel:
            return

        try:
            idx = int(sel) - 1
        except ValueError:
            return

        if idx < 0 or idx >= len(hits):
            pw("Nomor tidak valid.")
            return

        target = hits[idx]
        print()
        pi(f"Target offset : {target}  (0x{target:08X})")
        self._show_context(data, target)
        print()
        current_val = data[target]
        pi(f"Nilai saat ini: 0x{current_val:02X}  ({current_val} dec)")
        print()
        new_val = self._input_hex_byte()
        if new_val is None:
            return
        if new_val == current_val:
            pw("Nilai sama — tidak ada perubahan.")
            return
        self._write_byte(target, new_val, current_val)

    # ══════════════════════════════════════════════════════════
    #  MENU 5 — Analyze Metadata
    # ══════════════════════════════════════════════════════════
    def analyze_metadata(self):
        section("ANALYZE METADATA")
        if not self._validate():
            return
        data = self._read_file()
        if data is None:
            return

        fsize = len(data)
        md5   = hashlib.md5(data).hexdigest()

        pi(f"File     : {BOLD}{os.path.basename(self.filepath)}{RESET}")
        pi(f"Path     : {GRAY}{self.filepath}{RESET}")
        pi(f"Size     : {fsize:,} bytes  ({fsize/1024/1024:.2f} MB)")
        pi(f"MD5      : {GRAY}{md5}{RESET}")
        print()

        # ─ ftyp ──────────────────────────────────────────────
        ftyp_pos = data.find(b'ftyp')
        if ftyp_pos != -1:
            brand  = data[ftyp_pos+4:ftyp_pos+8].decode('latin-1').rstrip('\x00')
            minor  = struct.unpack('>I', data[ftyp_pos+8:ftyp_pos+12])[0]
            pi(f"Brand    : {CYAN}{brand}{RESET}  (minor ver {minor})")

        # ─ mvhd ──────────────────────────────────────────────
        mvhd_pos = data.find(b'mvhd')
        if mvhd_pos != -1:
            info = self._parse_mvhd(data[mvhd_pos + 4:])
            if info:
                dur = info.get('duration_sec', 0)
                pi(f"Duration : {dur:.3f}s  ({int(dur//60)}m {dur%60:.1f}s)")
                pi(f"Timescale: {info.get('timescale','?')} u/s")
                pi(f"Rate     : {info.get('rate', 0):.4f}x")
                pi(f"Volume   : {info.get('volume', 0)*100:.0f}%")
                pi(f"NextTrack: {info.get('next_track','?')}")
                if 'byte_44' in info:
                    b44 = info['byte_44']
                    pi(f"Byte[44] : {YELLOW}0x{b44:02X}{RESET}  ({b44} dec)")

        print()

        # ─ Track handlers ─────────────────────────────────────
        handlers = []
        pos = 0
        while True:
            pos = data.find(b'hdlr', pos)
            if pos == -1:
                break
            if pos + 20 < len(data):
                h = data[pos+12:pos+16].decode('latin-1').rstrip('\x00')
                if h.strip():
                    handlers.append(h)
            pos += 1
        if handlers:
            unique_h = list(dict.fromkeys(handlers))
            pi(f"Handlers : {', '.join(unique_h)}")

        trak_count = data.count(b'trak')
        pi(f"Tracks   : {trak_count}")

        # ─ udta / ilst (iTunes tags) ──────────────────────────
        print()
        has_udta = data.find(b'udta') != -1
        has_ilst = data.find(b'ilst') != -1
        (pok if has_udta else pw)(f"udta (user data) : {'ditemukan' if has_udta else 'tidak ada'}")
        (pok if has_ilst else pw)(f"ilst (iTunes tag): {'ditemukan' if has_ilst else 'tidak ada'}")

        if has_ilst:
            tag_map = {
                b'\xa9nam': 'Title ',
                b'\xa9ART': 'Artist',
                b'\xa9alb': 'Album ',
                b'\xa9day': 'Year  ',
                b'\xa9cmt': 'Comment',
                b'\xa9too': 'Encoder',
            }
            for tag_bytes, label in tag_map.items():
                tp = data.find(tag_bytes)
                if tp == -1:
                    continue
                try:
                    box_sz   = struct.unpack('>I', data[tp:tp+4])[0]
                    data_hdr = tp + 16          # skip box hdr + data box hdr
                    val_end  = tp + box_sz
                    if data_hdr < val_end <= len(data):
                        val = data[data_hdr:val_end].decode('utf-8', errors='replace').strip()
                        if val:
                            pi(f"  {label}: {WHITE}{val[:72]}{RESET}")
                except Exception:
                    pass

        # ─ Faststart check ────────────────────────────────────
        moov_pos = data.find(b'moov')
        mdat_pos = data.find(b'mdat')
        print()
        if moov_pos != -1 and mdat_pos != -1:
            fs = moov_pos < mdat_pos
            (pok if fs else pw)(f"Faststart: {'YA — moov sebelum mdat ✓' if fs else 'TIDAK — gunakan menu [6]'}")

    # ══════════════════════════════════════════════════════════
    #  MENU 6 — Faststart Optimizer
    # ══════════════════════════════════════════════════════════
    def faststart_optimizer(self):
        section("FASTSTART OPTIMIZER")
        if not self._validate():
            return

        if not self._backup():
            perr("Optimizer dibatalkan — backup gagal.")
            return

        data = self._read_file()
        if data is None:
            return

        boxes = self._parse_boxes(data)

        ftyp_box  = None
        moov_box  = None
        mdat_boxes = []
        rest_boxes = []

        for b in boxes:
            if b.type == 'ftyp':
                ftyp_box = b
            elif b.type == 'moov':
                moov_box = b
            elif b.type == 'mdat':
                mdat_boxes.append(b)
            elif b.type not in ('free', 'wide', 'skip'):
                rest_boxes.append(b)

        if moov_box is None:
            perr("'moov' tidak ditemukan. Tidak bisa optimize.")
            return
        if not mdat_boxes:
            perr("'mdat' tidak ditemukan.")
            return

        first_mdat = mdat_boxes[0]

        # Cek apakah sudah faststart
        if moov_box.offset < first_mdat.offset:
            pok("File sudah Faststart! moov sudah sebelum mdat. Tidak perlu diproses.")
            return

        pi(f"moov offset  : {moov_box.offset}  size={moov_box.size:,}")
        pi(f"mdat offset  : {first_mdat.offset}")
        pi("Memulai reorder moov → sebelum mdat...")
        print()

        # ─ Hitung shift offset yang benar ─────────────────────
        # Layout baru: [ftyp?][moov][rest_before_mdat][mdat+]
        # Hitung total bytes sebelum mdat di layout BARU
        new_before_mdat = 0
        if ftyp_box:
            new_before_mdat += ftyp_box.size
        new_before_mdat += moov_box.size
        for rb in rest_boxes:
            if rb.offset < first_mdat.offset:
                new_before_mdat += rb.size

        new_mdat_data_start      = new_before_mdat + 8   # +8: mdat header
        original_mdat_data_start = first_mdat.offset + 8

        shift = new_mdat_data_start - original_mdat_data_start
        pi(f"Chunk offset shift: {shift:+d} bytes")

        # Patch stco/co64 di dalam moov
        patched_moov = self._patch_chunk_offsets(moov_box.data, shift)
        print()

        # ─ Susun output baru ──────────────────────────────────
        parts = []
        if ftyp_box:
            parts.append(ftyp_box.data)
        parts.append(patched_moov)
        # box-box lain (bukan ftyp/moov/mdat/free)
        for rb in rest_boxes:
            parts.append(rb.data)
        # mdat di akhir
        for mb in mdat_boxes:
            parts.append(mb.data)

        new_data = b''.join(parts)

        # ─ Simpan sebagai file baru ───────────────────────────
        out_path = self.filepath.replace('.mp4', '_faststart.mp4')
        if out_path == self.filepath:
            out_path = self.filepath + '_faststart.mp4'

        try:
            with open(out_path, 'wb') as f:
                f.write(new_data)
            pok(f"Output tersimpan: {BOLD}{os.path.basename(out_path)}{RESET}")
            pi(f"Size: {len(new_data):,} bytes  ({len(new_data)/1024/1024:.2f} MB)")
        except Exception as e:
            perr(f"Gagal menulis output: {e}")

    # ══════════════════════════════════════════════════════════
    #  MENU 7 — Check Corruption
    # ══════════════════════════════════════════════════════════
    def check_corruption(self):
        section("CHECK CORRUPTION")
        if not self._validate():
            return
        data = self._read_file()
        if data is None:
            return

        issues   = []
        warnings = []
        ok_list  = []
        fsize    = len(data)

        # ── Check 1: ukuran minimal ───────────────────────────
        if fsize < 16:
            issues.append("File terlalu kecil (< 16 bytes)")
        else:
            ok_list.append(f"File size: {fsize:,} bytes")

        # ── Check 2: ftyp ─────────────────────────────────────
        ftyp_pos = data.find(b'ftyp')
        if ftyp_pos == -1:
            warnings.append("'ftyp' tidak ditemukan (bukan MP4 standar?)")
        elif ftyp_pos > 8:
            warnings.append(f"'ftyp' bukan di awal file (offset {ftyp_pos - 4})")
        else:
            ok_list.append(f"'ftyp' valid di offset {ftyp_pos - 4}")

        # ── Check 3: moov ─────────────────────────────────────
        moov_pos = data.find(b'moov')
        if moov_pos == -1:
            issues.append("'moov' TIDAK ditemukan — file corrupt atau truncated")
        else:
            moov_box_off  = moov_pos - 4
            moov_size_raw = struct.unpack('>I', data[moov_box_off:moov_pos])[0]
            if moov_box_off + moov_size_raw > fsize:
                issues.append(f"'moov' truncated — size {moov_size_raw:,} > sisa file")
            else:
                ok_list.append(f"'moov' valid — size {moov_size_raw:,} bytes")

        # ── Check 4: mvhd ─────────────────────────────────────
        mvhd_pos = data.find(b'mvhd')
        if mvhd_pos == -1:
            issues.append("'mvhd' tidak ada di dalam moov")
        else:
            ok_list.append(f"'mvhd' valid di offset {mvhd_pos - 4}")
            version = data[mvhd_pos + 4] if mvhd_pos + 4 < fsize else 255
            if version not in (0, 1):
                warnings.append(f"'mvhd' version tidak dikenal: {version}")
            else:
                ok_list.append(f"'mvhd' version {version} (valid)")

        # ── Check 5: mdat ─────────────────────────────────────
        mdat_pos = data.find(b'mdat')
        if mdat_pos == -1:
            issues.append("'mdat' tidak ditemukan — tidak ada media data")
        else:
            mdat_box_off  = mdat_pos - 4
            mdat_size_raw = struct.unpack('>I', data[mdat_box_off:mdat_pos])[0]
            if mdat_size_raw == 0:
                ok_list.append("'mdat' extends to EOF (valid)")
            elif mdat_box_off + mdat_size_raw > fsize:
                warnings.append(f"'mdat' mungkin truncated — size {mdat_size_raw:,}")
            else:
                ok_list.append(f"'mdat' valid — size {mdat_size_raw:,} bytes")

        # ── Check 6: total box coverage ───────────────────────
        boxes      = self._parse_boxes(data)
        total_cov  = sum(b.size for b in boxes)
        gap        = abs(total_cov - fsize)
        if gap > 16:
            warnings.append(f"Coverage gap {gap} bytes — ada padding atau unknown box")
        else:
            ok_list.append(f"Box coverage OK ({gap} bytes gap)")

        # ── Check 7: backup ───────────────────────────────────
        if os.path.exists(self.backup_path):
            ok_list.append(f"Backup ada: {os.path.basename(self.backup_path)}")

        # ── Report ────────────────────────────────────────────
        print()
        for item in ok_list:
            print(f"  {GREEN}✓{RESET}  {item}")
        for item in warnings:
            print(f"  {YELLOW}⚠{RESET}  {item}")
        for item in issues:
            print(f"  {RED}✗{RESET}  {item}")

        print()
        print(f"  {CYAN}{'━'*48}{RESET}")
        if not issues and not warnings:
            print(f"  {GREEN}{BOLD}STATUS: FILE SEHAT — SIAP DIPROSES ✓{RESET}")
        elif not issues:
            print(f"  {YELLOW}{BOLD}STATUS: MINOR WARNING ({len(warnings)} peringatan){RESET}")
        else:
            print(f"  {RED}{BOLD}STATUS: CORRUPT / BERMASALAH ({len(issues)} error){RESET}")
        print(f"  {CYAN}{'━'*48}{RESET}")

    # ══════════════════════════════════════════════════════════
    #  MENU 8 — Export Scan Report (JSON)
    # ══════════════════════════════════════════════════════════
    def export_scan_report(self):
        section("EXPORT SCAN REPORT")
        if not self._validate():
            return
        data = self._read_file()
        if data is None:
            return

        fsize = len(data)
        boxes = self._parse_boxes(data)

        report = {
            "tool":      "KYTHERA CORE v1.0",
            "timestamp": datetime.now().isoformat(timespec='seconds'),
            "file": {
                "path":       self.filepath,
                "name":       os.path.basename(self.filepath),
                "size_bytes": fsize,
                "size_mb":    round(fsize / 1024 / 1024, 3),
                "md5":        hashlib.md5(data).hexdigest(),
            },
            "boxes":    [],
            "mvhd":     {},
            "status":   {},
        }

        for b in boxes:
            entry = {"type": b.type, "size": b.size, "offset": b.offset}
            if b.type in ('moov', 'trak', 'udta', 'mdia', 'minf', 'stbl'):
                subs = self._parse_boxes(b.data[8:], b.offset + 8)
                entry["children"] = [{"type": s.type, "size": s.size} for s in subs]
            report["boxes"].append(entry)

        # mvhd detail
        mvhd_pos = data.find(b'mvhd')
        if mvhd_pos != -1:
            info = self._parse_mvhd(data[mvhd_pos + 4:])
            b44  = info.get('byte_44')
            report["mvhd"] = {
                "offset":           mvhd_pos - 4,
                "version":          info.get('version'),
                "timescale":        info.get('timescale'),
                "duration_units":   info.get('duration'),
                "duration_seconds": round(info.get('duration_sec', 0), 3),
                "rate":             round(info.get('rate', 0), 4),
                "volume_pct":       round(info.get('volume', 0) * 100, 1),
                "next_track_id":    info.get('next_track'),
                "byte_44_hex":      f"0x{b44:02X}" if b44 is not None else None,
                "byte_44_dec":      b44,
            }

        # Status flags
        moov_pos = data.find(b'moov')
        mdat_pos = data.find(b'mdat')
        report["status"] = {
            "has_ftyp":   data.find(b'ftyp') != -1,
            "has_moov":   moov_pos != -1,
            "has_mvhd":   mvhd_pos != -1,
            "has_mdat":   mdat_pos != -1,
            "faststart":  (moov_pos < mdat_pos) if (moov_pos != -1 and mdat_pos != -1) else False,
            "has_backup": os.path.exists(self.backup_path),
        }

        # ─ Simpan report ─────────────────────────────────────
        report_name = os.path.basename(self.filepath).replace('.mp4', '_kythera.json')
        report_path = os.path.join(os.path.dirname(os.path.abspath(self.filepath)), report_name)

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            pok(f"Report tersimpan: {BOLD}{report_name}{RESET}")
            pi(f"Path lengkap : {report_path}")
        except Exception as e:
            perr(f"Gagal menyimpan report: {e}")
            return

        # ─ Print ringkasan ────────────────────────────────────
        print()
        print(f"  {CYAN}{'─'*40}{RESET}")
        print(f"  {WHITE}RINGKASAN:{RESET}")
        for k, v in report["status"].items():
            icon = f"{GREEN}✓{RESET}" if v else f"{YELLOW}✗{RESET}"
            print(f"    {icon} {k:<14}: {v}")
        print(f"  {CYAN}{'─'*40}{RESET}")


# ══════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ══════════════════════════════════════════════════════════════
MENU_MAP = {
    '1': ('scan_structure',       'Scan MP4 Structure'),
    '2': ('detect_moov_mvhd',     'Detect moov/mvhd'),
    '3': ('repair_missing_moov',  'Repair Missing moov'),
    '4': ('patch_mvhd_byte',      'Patch mvhd Byte'),
    '5': ('analyze_metadata',     'Analyze Metadata'),
    '6': ('faststart_optimizer',  'Faststart Optimizer'),
    '7': ('check_corruption',     'Check Corruption'),
    '8': ('export_scan_report',   'Export Scan Report'),
}

def main():
    if len(sys.argv) < 3:
        print(f"{RED}Usage: python3 core.py <menu_number> <filepath>{RESET}")
        sys.exit(1)

    menu_num = sys.argv[1]
    filepath = sys.argv[2]

    entry = MENU_MAP.get(menu_num)
    if entry is None:
        print(f"{RED}[✗] Menu tidak dikenal: {menu_num}{RESET}")
        sys.exit(1)

    method_name, _ = entry
    engine = KytheraCoreEngine(filepath)

    try:
        getattr(engine, method_name)()
    except KeyboardInterrupt:
        print(f"\n  {YELLOW}[!] Dibatalkan (Ctrl+C).{RESET}")
        sys.exit(0)
    except Exception as exc:
        print(f"\n  {RED}[FATAL] {exc}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
