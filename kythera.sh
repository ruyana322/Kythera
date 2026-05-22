#!/data/data/com.termux/files/usr/bin/bash
CYAN='\033[96m'
WHITE='\033[97m'
YELLOW='\033[93m'
RED='\033[91m'
GREEN='\033[92m'
GRAY='\033[90m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_PY="$SCRIPT_DIR/core.py"

show_banner() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo '  __ __     __  __                   '
    echo ' / //_/_ __/ /_/ /  ___ _______ _    '
    echo '/ ,< / // / __/ _ \/ -_) __/ _ `/    '
    echo '/_/|_|\_, /\__/_//_/\__/_/  \_,_/     '
    echo '      /___/   [ C O R E ]              '
    echo -e "${RESET}"
    echo -e "${GRAY}${DIM}         ✧ by kythera ✧${RESET}"
    echo ""
}

show_menu() {
    echo -e "${CYAN}╭─────────────────────────────────────────╮${RESET}"
    echo -e "${CYAN}│${RESET}                                         ${CYAN}│${RESET}"
    echo -e "${CYAN}│${RESET}  ${CYAN}[1]${RESET} Scan MP4 Structure                 ${CYAN}│${RESET}"
    echo -e "${CYAN}│${RESET}  ${CYAN}[2]${RESET} Detect moov/mvhd                   ${CYAN}│${RESET}"
    echo -e "${CYAN}│${RESET}  ${CYAN}[3]${RESET} Repair Missing moov                ${CYAN}│${RESET}"
    echo -e "${CYAN}│${RESET}  ${YELLOW}[4]${RESET} Patch mvhd Byte  ${YELLOW}★ FUNGSI UTAMA${RESET}    ${CYAN}│${RESET}"
    echo -e "${CYAN}│${RESET}  ${CYAN}[5]${RESET} Analyze Metadata                   ${CYAN}│${RESET}"
    echo -e "${CYAN}│${RESET}  ${CYAN}[6]${RESET} Faststart Optimizer                ${CYAN}│${RESET}"
    echo -e "${CYAN}│${RESET}  ${CYAN}[7]${RESET} Check Corruption                   ${CYAN}│${RESET}"
    echo -e "${CYAN}│${RESET}  ${CYAN}[8]${RESET} Export Scan Report                 ${CYAN}│${RESET}"
    echo -e "${CYAN}│${RESET}                                         ${CYAN}│${RESET}"
    echo -e "${CYAN}│${RESET}  ${RED}[0]${RESET} Exit System                        ${CYAN}│${RESET}"
    echo -e "${CYAN}│${RESET}                                         ${CYAN}│${RESET}"
    echo -e "${CYAN}╰─────────────────────────────────────────╯${RESET}"
    echo ""
    echo -ne "${CYAN}> ${WHITE}Select module (0-8): ${RESET}"
}

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

prompt_filepath() {
    echo ""
    echo -e "${CYAN}╭─────────────────────────────────────────╮${RESET}"
    echo -e "${CYAN}│${RESET}  ${WHITE}Path file MP4:${RESET}                          ${CYAN}│${RESET}"
    echo -e "${CYAN}│${RESET}  ${GRAY}(drag & drop ke Termux OK)${RESET}               ${CYAN}│${RESET}"
    echo -e "${CYAN}╰─────────────────────────────────────────╯${RESET}"
    echo -ne "${CYAN}> ${RESET}"
    read -r raw_path

    raw_path="${raw_path//\'/}"
    raw_path="${raw_path//\"/}"
    raw_path="${raw_path/#\~/$HOME}"
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
    echo -e "  ${GREEN}[✓]${RESET} ${WHITE}$(basename "$raw_path")${RESET}"
    echo -e "  ${GRAY}    $(du -h "$raw_path" | cut -f1) · ${raw_path}${RESET}"
    return 0
}

run_core() {
    local menu_num="$1"
    local filepath="$2"

    echo ""
    echo -e "${GRAY}  ─────────────────────────────────────────${RESET}"
    python3 "$CORE_PY" "$menu_num" "$filepath"
    local rc=$?
    echo -e "${GRAY}  ─────────────────────────────────────────${RESET}"

    if [[ $rc -eq 0 ]]; then
        echo -e "  ${GREEN}[✓] Proses selesai.${RESET}"
    else
        echo -e "  ${RED}[✗] Error code: $rc${RESET}"
    fi
}

pause_continue() {
    echo ""
    echo -e "  ${GRAY}Tekan ${WHITE}Enter${GRAY} untuk kembali ke menu...${RESET}"
    read -r
}

handle_menu() {
    local choice="$1"
    local label="$2"

    echo ""
    echo -e "  ${CYAN}[${choice}]${RESET} ${BOLD}${WHITE}${label}${RESET}"

    if [[ "$choice" == "4" ]]; then
        echo ""
        echo -e "  ${YELLOW}  ⚠  Auto-backup (.bak) dibuat sebelum modifikasi.${RESET}"
        echo -e "  ${RED}  ⚠  Pastikan file tidak sedang dipakai proses lain.${RESET}"
    elif [[ "$choice" == "6" ]]; then
        echo ""
        echo -e "  ${YELLOW}  ⚡ Output disimpan sebagai *_faststart.mp4${RESET}"
        echo -e "  ${GRAY}     File asli tidak akan diubah.${RESET}"
    fi

    if ! prompt_filepath; then
        pause_continue
        return
    fi

    run_core "$choice" "$SELECTED_FILE"
    pause_continue
}

main() {
    if ! check_deps; then
        echo -e "\n  ${RED}Dependency check gagal. Perbaiki masalah di atas lalu jalankan ulang.${RESET}\n"
        exit 1
    fi

    while true; do
        show_banner
        show_menu
        read -r choice

        case "$choice" in
            0)
                clear
                echo ""
                echo -e "  ${CYAN}${BOLD}KYTHERA CORE${RESET} ${GRAY}// Session terminated.${RESET}"
                echo -e "  ${GRAY}             Goodbye.${RESET}"
                echo ""
                exit 0
                ;;
            1) handle_menu "1" "Scan MP4 Structure" ;;
            2) handle_menu "2" "Detect moov / mvhd" ;;
            3) handle_menu "3" "Repair Missing moov" ;;
            4) handle_menu "4" "Patch mvhd Byte" ;;
            5) handle_menu "5" "Analyze Metadata" ;;
            6) handle_menu "6" "Faststart Optimizer" ;;
            7) handle_menu "7" "Check Corruption" ;;
            8) handle_menu "8" "Export Scan Report" ;;
            "") ;;
            *)
                echo -e "\n  ${RED}[✗] Input tidak valid: '${choice}'${RESET}"
                sleep 1
                ;;
        esac
    done
}

main
