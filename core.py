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
    def patch_mvhd_byte(self):
        section("PATCH mvhd BYTE  ★")
        if not self._validate():
            return

        # ── BACKUP dulu, sebelum baca ulang atau modifikasi ──
        if not self._backup():
            perr("Patch dibatalkan — backup gagal dibuat.")
            return

        data = self._read_file()
        if data is None:
            return

        mvhd_pos = data.find(b'mvhd')
        if mvhd_pos == -1:
            perr("'mvhd' tidak ditemukan. File bukan MP4 valid.")
            return

        # Target: byte ke-44 dihitung dari awal string 'mvhd'
        # Layout: [size 4B][mvhd 4B][version 1B][flags 3B]
        #         [ctime 4B][mtime 4B][timescale 4B][duration 4B]
        #         [rate 4B][volume 2B][reserved 10B]
        #         [matrix starts at offset 36 from 'mvhd']
        # Byte ke-44 dari 'm' = indeks 44 dari mvhd_pos
        target_abs = mvhd_pos + 44

        if target_abs >= len(data):
            perr(f"Offset target ({target_abs}) melebihi ukuran file ({len(data)}).")
            return

        current_val = data[target_abs]

        pi(f"'mvhd' ditemukan di offset    : {mvhd_pos}")
        pi(f"Target offset (mvhd + 44)     : {target_abs}")
        pi(f"Nilai byte saat ini           : {BOLD}0x{current_val:02X}{RESET}  ({current_val} dec)")

        # ─ Tampilkan context bytes ────────────────────────────
        ctx_s = max(0, target_abs - 6)
        ctx_e = min(len(data), target_abs + 7)
        print()
        print(f"  {GRAY}Context hex (offset {ctx_s}–{ctx_e-1}):{RESET}")
        hex_parts = []
        for i, b in enumerate(data[ctx_s:ctx_e]):
            abs_i = ctx_s + i
            if abs_i == target_abs:
                hex_parts.append(f"{YELLOW}{BOLD}[{b:02X}]{RESET}")
            else:
                hex_parts.append(f"{GRAY}{b:02X}{RESET}")
        print("  " + " ".join(hex_parts))
        print()

        # ─ Input nilai baru ───────────────────────────────────
        print(f"  {CYAN}Masukkan nilai hex baru (1 byte, contoh: 01  37  FF  00):{RESET}")
        try:
            raw = input(f"  {YELLOW}» {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n  {YELLOW}Dibatalkan.{RESET}")
            return

        raw = raw.replace('0x', '').replace('0X', '').strip()

        if not raw:
            pw("Tidak ada input. Dibatalkan.")
            return
        if len(raw) > 2:
            perr(f"Input '{raw}' terlalu panjang — maksimal 2 karakter hex (1 byte).")
            return
        try:
            new_val = int(raw, 16)
        except ValueError:
            perr(f"Input tidak valid: '{raw}'. Gunakan hex seperti: 01  FF  3A")
            return

        if new_val == current_val:
            pw(f"Nilai sama (0x{new_val:02X}) — tidak ada perubahan, tidak ditulis.")
            return

        # ─ Konfirmasi ─────────────────────────────────────────
        print()
        print(f"  {YELLOW}{'━'*46}{RESET}")
        print(f"  {YELLOW}KONFIRMASI PATCH:{RESET}")
        print(f"    Offset   : {target_abs}")
        print(f"    Sebelum  : 0x{current_val:02X}  ({current_val})")
        print(f"    Sesudah  : {BOLD}0x{new_val:02X}  ({new_val}){RESET}")
        print(f"    Backup   : {os.path.basename(self.backup_path)}")
        print(f"  {YELLOW}{'━'*46}{RESET}")
        print()
        print(f"  {RED}Lanjutkan? Hanya byte ini yang diubah. (y/N){RESET}")
        try:
            confirm = input(f"  {YELLOW}» {RESET}").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(f"\n  {YELLOW}Dibatalkan.{RESET}")
            return

        if confirm != 'y':
            pw("Patch dibatalkan oleh user.")
            return

        # ─ Tulis patch — hanya 1 byte, surgis, aman ──────────
        try:
            with open(self.filepath, 'rb+') as f:
                f.seek(target_abs)
                f.write(bytes([new_val]))
            pok(f"Patch sukses! Offset {target_abs} → 0x{new_val:02X}")
            pi(f"Backup original ada di: {self.backup_path}")
        except PermissionError:
            perr("Permission denied — tidak bisa menulis ke file.")
        except Exception as e:
            perr(f"Gagal menulis: {e}")

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
