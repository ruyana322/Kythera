#!/usr/bin/env python3

import sys
import os
import struct
import shutil
import json
import hashlib
from datetime import datetime

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

class MP4Box:
    __slots__ = ('size', 'type', 'offset', 'data')

    def __init__(self, size, box_type, offset, data):
        self.size   = size
        self.type   = box_type
        self.offset = offset
        self.data   = data

    def __repr__(self):
        return f"MP4Box(type={self.type!r}, size={self.size}, offset={self.offset})"

class KytheraCoreEngine:
    def __init__(self, filepath: str):
        self.filepath    = filepath
        self.backup_path = filepath + '.bak'

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

    def _read_file(self) -> bytes | None:
        try:
            with open(self.filepath, 'rb') as f:
                return f.read()
        except Exception as e:
            perr(f"Gagal membaca file: {e}")
            return None

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

    def _parse_boxes(self, data: bytes, base_offset: int = 0) -> list[MP4Box]:
        boxes = []
        pos   = 0
        end   = len(data)

        while pos + 8 <= end:
            try:
                raw_size = struct.unpack('>I', data[pos:pos+4])[0]
                box_type = data[pos+4:pos+8].decode('latin-1')

                if raw_size == 1:
                    if pos + 16 > end:
                        break
                    size = struct.unpack('>Q', data[pos+8:pos+16])[0]
                elif raw_size == 0:
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

    def _parse_mvhd(self, mvhd_payload: bytes) -> dict:
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

    def scan_structure(self):
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

    def detect_moov_mvhd(self):
        if not self._validate():
            return
        data = self._read_file()
        if data is None:
            return

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

        mvhd_pos = data.find(b'mvhd')
        if mvhd_pos == -1:
            perr("'mvhd' atom TIDAK ditemukan.")
        else:
            mvhd_box_offset = mvhd_pos - 4
            mvhd_size       = struct.unpack('>I', data[mvhd_box_offset:mvhd_pos])[0]
            pok(f"'mvhd' ditemukan  offset={mvhd_box_offset}  size={mvhd_size} bytes")

            payload = data[mvhd_pos + 4:]
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

    def repair_missing_moov(self):
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

        moof_pos = data.find(b'moof')
        if moof_pos != -1:
            pw(f"'moof' (fragment) ditemukan di offset {moof_pos - 4}")
            pw("File ini adalah Fragmented MP4 — butuh re-mux, bukan repair biasa.")
            pi("Coba di Termux:")
            print(f"    {CYAN}ffmpeg -i input.mp4 -c copy -movflags faststart output.mp4{RESET}")
            return

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
                data = self._read_file()
                if data is None:
                    return

            elif mode == '2':
                self._search_pattern(data)

            else:
                pw("Pilihan tidak valid.")

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

        raw = 
