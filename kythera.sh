#!/data/data/com.termux/files/usr/bin/bash
# ╔══════════════════════════════════════════════════════════╗
# ║          KYTHERA CORE — kythera.sh                      ║
# ║          Bash UI Wrapper & Launcher                     ║
# ║          MP4 Binary Structure & Metadata Toolkit        ║
# ╚══════════════════════════════════════════════════════════╝

# ── ANSI COLOR PALETTE ────────────────────────────────────────
CYAN='\033[96m'
LCYAN='\033[36m'
WHITE='\033[97m'
YELLOW='\033[93m'
RED='\033[91m'
GREEN='\033[92m'
GRAY='\033[90m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

# ── SCRIPT LOCATION ───────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_PY="$SCRIPT_DIR/core.py"

# ── TERMINAL WIDTH & BOX HELPERS ─────────────────────────────
TW=$(tput cols 2>/dev/null || echo 60)
# Clamp antara 40–80 biar aman
(( TW < 40 )) && TW=40
(( TW > 80 )) && TW=80

BOX_W=$(( TW - 4 ))   # lebar dalam box (exclude 2 border + 2 indent)
INDENT="  "            # 2 spasi indent kiri

# Cetak garis horizontal box
box_line() {
    # $1 = karakter kiri, $2 = fill, $3 = karakter kanan
    local inner
    inner=$(printf '%0.s'"$2" $(seq 1 $BOX_W))
    printf "${INDENT}${CYAN}%s%s%s${RESET}\n" "$1" "$inner" "$3"
}

# Cetak baris konten box, teks rata kiri
# $1 = teks (tanpa ANSI), $2 = teks dengan ANSI (opsional)
box_row() {
    local raw="$1"
    local colored="${2:-$1}"
    local raw_len=${#raw}
    local pad=$(( BOX_W - raw_len - 2 ))
    (( pad < 0 )) && pad=0
    local spaces
    spaces=$(printf '%*s' "$pad" '')
    printf "${INDENT}${CYAN}║${RESET} %b%s ${CYAN}║${RESET}\n" "$colored" "$spaces"
}

# Cetak baris kosong dalam box
box_empty() {
    local inner
    inner=$(printf '%*s' "$BOX_W" '')
    printf "${INDENT}${CYAN}║%s║${RESET}\n" "$inner"
}

# Teks centered dalam lebar BOX_W (tanpa border)
center_text() {
    local text="$1"
    local len=${#text}
    local total=$(( BOX_W ))
    local lpad=$(( (total - len) / 2 ))
    local rpad=$(( total - len - lpad ))
    printf '%*s%s%*s' "$lpad" '' "$text" "$rpad" ''
}

# ── BANNER ────────────────────────────────────────────────────
show_banner() {
    clear

    # ASCII KYTHERA — compact 5-line version
    echo -e "${CYAN}${BOLD}"
    if (( TW >= 60 )); then
        cat << 'EOF'
  ██╗  ██╗██╗   ██╗████████╗██╗  ██╗███████╗██████╗  █████╗
  ██║ ██╔╝╚██╗ ██╔╝╚══██╔══╝██║  ██║██╔════╝██╔══██╗██╔══██╗
  █████╔╝  ╚████╔╝    ██║   ███████║█████╗  ██████╔╝███████║
  ██╔═██╗   ╚██╔╝     ██║   ██╔══██║██╔══╝  ██╔══██╗██╔══██║
  ██║  ██╗   ██║      ██║   ██║  ██║███████╗██║  ██║██║  ██║
  ╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
EOF
    else
        # Fallback teks biasa kalau layar sempit
        echo -e "  ${BOLD}${CYAN}[ KYTHERA ]${RESET}"
    fi
    echo -e "${RESET}"

    # CORE subtitle
    echo -e "${CYAN}${BOLD}"
    if (( TW >= 50 )); then
        cat << 'EOF'
     ██████╗ ██████╗ ██████╗ ███████╗
    ██╔════╝██╔═══██╗██╔══██╗██╔════╝
    ██║     ██║   ██║██████╔╝█████╗
    ██║     ██║   ██║██╔══██╗██╔══╝
    ╚██████╗╚██████╔╝██║  ██║███████╗
     ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
EOF
    fi
    echo -e "${RESET}"

    # Credit "by kythera" rata kanan
    local credit="${GRAY}${DIM}by kythera${RESET}"
    local credit_raw="by kythera"
    local pad=$(( TW - ${#credit_raw} - 1 ))
    printf "%${pad}s${GRAY}${DIM}%s${RESET}\n" "" "$credit_raw"

    echo ""

    # Tagline box
    box_line "┌" "─" "┐"
    local tl1="MP4 Binary Structure & Metadata Toolkit"
    local tl2="Hex Manipulation · Repair · Faststart"
    box_row "$tl1" "${WHITE}$tl1${RESET}"
    box_row "$tl2" "${GRAY}$tl2${RESET}"
    box_line "└" "─" "┘"

    echo ""
}

# ── MAIN MENU ─────────────────────────────────────────────────
show_menu() {
    # Header
    box_line "╔" "═" "╗"
    local hdr
    hdr=$(center_text "M A I N  M E N U")
    printf "${INDENT}${CYAN}║${BOLD}${WHITE}%s${RESET}${CYAN}║${RESET}\n" "$hdr"
    box_line "╠" "═" "╣"
    box_empty

    # Menu items
    local items=(
        "1|${CYAN}[1]${RESET}  Scan MP4 Structure"
        "2|${CYAN}[2]${RESET}  Detect moov / mvhd"
        "3|${CYAN}[3]${RESET}  Repair Missing moov"
        "4|${YELLOW}[4]${RESET}  Patch mvhd Byte  ${YELLOW}★ FUNGSI UTAMA${RESET}"
        "5|${CYAN}[5]${RESET}  Analyze Metadata"
        "6|${CYAN}[6]${RESET}  Faststart Optimizer"
        "7|${CYAN}[7]${RESET}  Check Corruption"
        "8|${CYAN}[8]${RESET}  Export Scan Report"
    )

    for entry in "${items[@]}"; do
        local num="${entry%%|*}"
        local display="${entry#*|}"

        # Hitung raw length (strip ANSI untuk padding)
        local raw
        raw=$(echo -e "   $display" | sed 's/\x1b\[[0-9;]*m//g')
        local raw_len=${#raw}
        local pad=$(( BOX_W - raw_len - 1 ))
        (( pad < 0 )) && pad=0
        local spaces
        spaces=$(printf '%*s' "$pad" '')

        printf "${INDENT}${CYAN}║${RESET}   %b%s ${CYAN}║${RESET}\n" "$display" "$spaces"
    done

    box_empty
    box_line "╠" "═" "╣"

    # Exit
    local exit_raw="   [0]  Exit"
    local exit_len=${#exit_raw}
    local exit_pad=$(( BOX_W - exit_len - 1 ))
    (( exit_pad < 0 )) && exit_pad=0
    local exit_spaces
    exit_spaces=$(printf '%*s' "$exit_pad" '')
    printf "${INDENT}${CYAN}║${RESET}   ${RED}[0]${RESET}  Exit%s ${CYAN}║${RESET}\n" "$exit_spaces"

    box_line "╚" "═" "╝"
    echo ""
}

# ── DEPENDENCY CHECK ──────────────────────────────────────────
check_deps() {
    local ok=1

    if ! command -v python3 &>/dev/null; then
        echo -e "${INDENT}${RED}[✗]${RESET} Python3 tidak terinstall!"
        echo -e "${INDENT}${YELLOW}    ➜  pkg install python${RESET}"
        ok=0
    fi

    if [[ ! -f "$CORE_PY" ]]; then
        echo -e "${INDENT}${RED}[✗]${RESET} core.py tidak ditemukan di: ${GRAY}$SCRIPT_DIR${RESET}"
        ok=0
    fi

    [[ $ok -eq 1 ]]
}

# ── INPUT FILE PATH ───────────────────────────────────────────
prompt_filepath() {
    echo ""
    box_line "┌" "─" "┐"
    local lbl="Masukkan path file MP4:"
    box_row "$lbl" "${WHITE}$lbl${RESET}"
    local hint="(bisa drag & drop di Termux)"
    box_row "$hint" "${GRAY}$hint${RESET}"
    box_line "└" "─" "┘"
    echo -ne "${INDENT}${YELLOW}» ${RESET}"
    read -r raw_path

    # Bersihkan quotes dan expand tilde
    raw_path="${raw_path//\'/}"
    raw_path="${raw_path//\"/}"
    raw_path="${raw_path/#\~/$HOME}"
    raw_path="$(echo "$raw_path" | xargs)"

    if [[ -z "$raw_path" ]]; then
        echo -e "\n${INDENT}${RED}[✗] Path tidak boleh kosong.${RESET}"
        return 1
    fi

    if [[ ! -f "$raw_path" ]]; then
        echo -e "\n${INDENT}${RED}[✗] File tidak ditemukan:${RESET} ${GRAY}$raw_path${RESET}"
        return 1
    fi

    SELECTED_FILE="$raw_path"
    echo -e "${INDENT}${GREEN}[✓]${RESET} ${WHITE}$(basename "$raw_path")${RESET}"
    echo -e "${INDENT}${GRAY}    $(du -h "$raw_path" | cut -f1) · ${raw_path}${RESET}"
    return 0
}

# ── RUN PYTHON CORE ───────────────────────────────────────────
run_core() {
    local menu_num="$1"
    local filepath="$2"

    echo ""
    box_line "─" "─" "─" 2>/dev/null || \
        echo -e "${INDENT}${GRAY}────────────────────────────────────────────────────${RESET}"
    python3 "$CORE_PY" "$menu_num" "$filepath"
    local rc=$?
    echo -e "${INDENT}${GRAY}────────────────────────────────────────────────────${RESET}"

    if [[ $rc -eq 0 ]]; then
        echo -e "${INDENT}${GREEN}[+] Proses selesai.${RESET}"
    else
        echo -e "${INDENT}${RED}[✗] Core keluar dengan error code $rc.${RESET}"
    fi
}

# ── PAUSE ─────────────────────────────────────────────────────
pause_continue() {
    echo ""
    echo -e "${INDENT}${GRAY}Tekan ${WHITE}Enter${GRAY} untuk kembali ke menu...${RESET}"
    read -r
}

# ── MENU HANDLER ──────────────────────────────────────────────
handle_menu_1_to_8() {
    local choice="$1"
    local label="$2"

    echo ""
    echo -e "${INDENT}${CYAN}[${choice}]${RESET} ${BOLD}${WHITE}${label}${RESET}"

    if [[ "$choice" == "4" ]]; then
        echo ""
        echo -e "${INDENT}${YELLOW}  ⚠  Auto-backup (.bak) akan dibuat sebelum modifikasi.${RESET}"
        echo -e "${INDENT}${RED}  ⚠  Pastikan file tidak sedang digunakan proses lain.${RESET}"
    elif [[ "$choice" == "6" ]]; then
        echo ""
        echo -e "${INDENT}${YELLOW}  ⚡ Output disimpan sebagai file baru (*_faststart.mp4)${RESET}"
        echo -e "${INDENT}${GRAY}     File asli tidak akan diubah.${RESET}"
    fi

    if ! prompt_filepath; then
        pause_continue
        return
    fi

    run_core "$choice" "$SELECTED_FILE"
    pause_continue
}

# ── MAIN LOOP ─────────────────────────────────────────────────
main() {
    if ! check_deps; then
        echo -e "\n${INDENT}${RED}Dependency check gagal. Perbaiki masalah di atas lalu jalankan ulang.${RESET}\n"
        exit 1
    fi

    while true; do
        show_banner
        show_menu

        echo -ne "${INDENT}${CYAN}Pilih menu ${YELLOW}[0-8] »${RESET} "
        read -r choice

        case "$choice" in
            0)
                clear
                echo -e "\n${INDENT}${CYAN}${BOLD}KYTHERA CORE${RESET} ${GRAY}// Session terminated. Goodbye.${RESET}\n"
                exit 0
                ;;
            1) handle_menu_1_to_8 "1" "Scan MP4 Structure" ;;
            2) handle_menu_1_to_8 "2" "Detect moov / mvhd" ;;
            3) handle_menu_1_to_8 "3" "Repair Missing moov" ;;
            4) handle_menu_1_to_8 "4" "Patch mvhd Byte" ;;
            5) handle_menu_1_to_8 "5" "Analyze Metadata" ;;
            6) handle_menu_1_to_8 "6" "Faststart Optimizer" ;;
            7) handle_menu_1_to_8 "7" "Check Corruption" ;;
            8) handle_menu_1_to_8 "8" "Export Scan Report" ;;
            "") ;;
            *)
                echo -e "\n${INDENT}${RED}[✗] Pilihan tidak valid: '${choice}'${RESET}"
                sleep 1
                ;;
        esac
    done
}

main
