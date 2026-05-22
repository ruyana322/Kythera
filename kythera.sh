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

# ── SCRIPT LOCATION (agar core.py bisa ditemukan) ─────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_PY="$SCRIPT_DIR/core.py"

# ── BANNER ────────────────────────────────────────────────────
show_banner() {
    clear
    echo -e "${CYAN}${BOLD}"
    cat << 'EOF'
  ██╗  ██╗██╗   ██╗████████╗██╗  ██╗███████╗██████╗  █████╗
  ██║ ██╔╝╚██╗ ██╔╝╚══██╔══╝██║  ██║██╔════╝██╔══██╗██╔══██╗
  █████╔╝  ╚████╔╝    ██║   ███████║█████╗  ██████╔╝███████║
  ██╔═██╗   ╚██╔╝     ██║   ██╔══██║██╔══╝  ██╔══██╗██╔══██║
  ██║  ██╗   ██║      ██║   ██║  ██║███████╗██║  ██║██║  ██║
  ╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
EOF
    echo -e "${RESET}"
    echo -e "${CYAN}${BOLD}"
    cat << 'EOF'
     ██████╗ ██████╗ ██████╗ ███████╗
    ██╔════╝██╔═══██╗██╔══██╗██╔════╝
    ██║     ██║   ██║██████╔╝█████╗
    ██║     ██║   ██║██╔══██╗██╔══╝
    ╚██████╗╚██████╔╝██║  ██║███████╗
     ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
EOF
    echo -e "${RESET}"

    # Credit pojok kanan — "by kythera"
    local tw
    tw=$(tput cols 2>/dev/null || echo 70)
    local credit="by kythera"
    local pad=$(( tw - ${#credit} - 1 ))
    printf "%${pad}s${GRAY}${DIM}%s${RESET}\n" "" "$credit"

    echo ""
    echo -e "${CYAN}  ┌──────────────────────────────────────────────────────┐${RESET}"
    echo -e "${CYAN}  │${WHITE}      MP4 Binary Structure & Metadata Toolkit         ${CYAN}│${RESET}"
    echo -e "${CYAN}  │${GRAY}      Hex Manipulation · Repair · Faststart            ${CYAN}│${RESET}"
    echo -e "${CYAN}  └──────────────────────────────────────────────────────┘${RESET}"
    echo ""
}

# ── MAIN MENU ─────────────────────────────────────────────────
show_menu() {
    echo -e "${CYAN}  ╔══════════════════════════════════════════════════════╗${RESET}"
    echo -e "${CYAN}  ║${BOLD}${WHITE}                    M A I N  M E N U                 ${RESET}${CYAN}║${RESET}"
    echo -e "${CYAN}  ╠══════════════════════════════════════════════════════╣${RESET}"
    echo -e "${CYAN}  ║${RESET}                                                      ${CYAN}║${RESET}"
    echo -e "${CYAN}  ║${RESET}   ${CYAN}[1]${RESET}  Scan MP4 Structure                           ${CYAN}║${RESET}"
    echo -e "${CYAN}  ║${RESET}   ${CYAN}[2]${RESET}  Detect moov / mvhd                           ${CYAN}║${RESET}"
    echo -e "${CYAN}  ║${RESET}   ${CYAN}[3]${RESET}  Repair Missing moov                          ${CYAN}║${RESET}"
    echo -e "${CYAN}  ║${RESET}   ${YELLOW}[4]${RESET}  Patch mvhd Byte  ${YELLOW}★ FUNGSI UTAMA${RESET}            ${CYAN}║${RESET}"
    echo -e "${CYAN}  ║${RESET}   ${CYAN}[5]${RESET}  Analyze Metadata                             ${CYAN}║${RESET}"
    echo -e "${CYAN}  ║${RESET}   ${CYAN}[6]${RESET}  Faststart Optimizer                          ${CYAN}║${RESET}"
    echo -e "${CYAN}  ║${RESET}   ${CYAN}[7]${RESET}  Check Corruption                             ${CYAN}║${RESET}"
    echo -e "${CYAN}  ║${RESET}   ${CYAN}[8]${RESET}  Export Scan Report                           ${CYAN}║${RESET}"
    echo -e "${CYAN}  ║${RESET}                                                      ${CYAN}║${RESET}"
    echo -e "${CYAN}  ╠══════════════════════════════════════════════════════╣${RESET}"
    echo -e "${CYAN}  ║${RESET}   ${RED}[0]${RESET}  Exit                                          ${CYAN}║${RESET}"
    echo -e "${CYAN}  ╚══════════════════════════════════════════════════════╝${RESET}"
    echo ""
}

# ── DEPENDENCY CHECK ──────────────────────────────────────────
check_deps() {
    local ok=1

    if ! command -v python3 &>/dev/null; then
        echo -e "  ${RED}[✗]${RESET} Python3 tidak terinstall!"
        echo -e "  ${YELLOW}    ➜  pkg install python${RESET}"
        ok=0
    fi

    if [[ ! -f "$CORE_PY" ]]; then
        echo -e "  ${RED}[✗]${RESET} core.py tidak ditemukan di: ${GRAY}$SCRIPT_DIR${RESET}"
        ok=0
    fi

    [[ $ok -eq 1 ]]
}

# ── INPUT FILE PATH ───────────────────────────────────────────
prompt_filepath() {
    echo -e "  ${CYAN}┌──────────────────────────────────────────────────────┐${RESET}"
    echo -e "  ${CYAN}│${WHITE}  Masukkan path file MP4 (bisa drag & drop di Termux): ${CYAN}│${RESET}"
    echo -e "  ${CYAN}└──────────────────────────────────────────────────────┘${RESET}"
    echo -ne "  ${YELLOW}» ${RESET}"
    read -r raw_path

    # Bersihkan quotes dan expand tilde
    raw_path="${raw_path//\'/}"
    raw_path="${raw_path//\"/}"
    raw_path="${raw_path/#\~/$HOME}"
    # Trim leading/trailing spaces
    raw_path="$(echo "$raw_path" | xargs)"

    if [[ -z "$raw_path" ]]; then
        echo -e "\n  ${RED}[✗] Path tidak boleh kosong.${RESET}"
        return 1
    fi

    if [[ ! -f "$raw_path" ]]; then
        echo -e "\n  ${RED}[✗] File tidak ditemukan:${RESET} ${GRAY}$raw_path${RESET}"
        return 1
    fi

    SELECTED_FILE="$raw_path"
    echo -e "  ${GREEN}[✓] File:${RESET} ${WHITE}$(basename "$raw_path")${RESET}"
    echo -e "  ${GRAY}      $(du -h "$raw_path" | cut -f1) — ${raw_path}${RESET}"
    return 0
}

# ── RUN PYTHON CORE ───────────────────────────────────────────
run_core() {
    local menu_num="$1"
    local filepath="$2"

    echo ""
    echo -e "  ${GRAY}────────────────────────────────────────────────────${RESET}"
    python3 "$CORE_PY" "$menu_num" "$filepath"
    local rc=$?
    echo -e "  ${GRAY}────────────────────────────────────────────────────${RESET}"

    if [[ $rc -eq 0 ]]; then
        echo -e "  ${GREEN}[+] Proses selesai.${RESET}"
    else
        echo -e "  ${RED}[✗] Core keluar dengan error code $rc.${RESET}"
    fi
}

# ── PAUSE ─────────────────────────────────────────────────────
pause_continue() {
    echo ""
    echo -e "  ${GRAY}Tekan ${WHITE}Enter${GRAY} untuk kembali ke menu...${RESET}"
    read -r
}

# ── MENU HANDLER ──────────────────────────────────────────────
handle_menu_1_to_8() {
    local choice="$1"
    local label="$2"

    echo ""
    echo -e "  ${CYAN}[${choice}]${RESET} ${BOLD}${WHITE}${label}${RESET}"

    # Peringatan khusus menu 4 dan 6 (modifikasi file)
    if [[ "$choice" == "4" ]]; then
        echo ""
        echo -e "  ${YELLOW}  ⚠  Auto-backup (.bak) akan dibuat sebelum modifikasi.${RESET}"
        echo -e "  ${RED}  ⚠  Pastikan file tidak sedang digunakan proses lain.${RESET}"
    elif [[ "$choice" == "6" ]]; then
        echo ""
        echo -e "  ${YELLOW}  ⚡ Output disimpan sebagai file baru (*_faststart.mp4)${RESET}"
        echo -e "  ${GRAY}     File asli tidak akan diubah.${RESET}"
    fi

    echo ""
    local filepath
    if ! prompt_filepath; then
        pause_continue
        return
    fi
    filepath="$SELECTED_FILE"

    run_core "$choice" "$filepath"
    pause_continue
}

# ── MAIN LOOP ─────────────────────────────────────────────────
main() {
    # Pre-flight check
    if ! check_deps; then
        echo -e "\n  ${RED}Dependency check gagal. Perbaiki masalah di atas lalu jalankan ulang.${RESET}\n"
        exit 1
    fi

    while true; do
        show_banner
        show_menu

        echo -ne "  ${CYAN}Pilih menu${RESET} ${YELLOW}[0-8] »${RESET} "
        read -r choice

        case "$choice" in
            0)
                clear
                echo -e "\n  ${CYAN}${BOLD}KYTHERA CORE${RESET} ${GRAY}// Session terminated. Goodbye.${RESET}\n"
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
            "")
                # Enter kosong — ulangi menu saja
                ;;
            *)
                echo -e "\n  ${RED}[✗] Pilihan tidak dikenal: '${choice}'${RESET}"
                sleep 1
                ;;
        esac
    done
}

main
