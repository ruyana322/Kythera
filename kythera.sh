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

SELECTED_FILE=""
FILE_STATUS="${GRAY}no file loaded${RESET}"
SESSION_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
DIVIDER="${GRAY} ───────────────────────────────────────────────────────────${RESET}"

update_file_status() {
    local fp="$1"
    if [[ -z "$fp" ]]; then
        FILE_STATUS="${GRAY}no file loaded${RESET}"
        return
    fi
    local result
    result=$(python3 "$CORE_PY" "check_status" "$fp" 2>/dev/null)
    if [[ -z "$result" ]]; then
        FILE_STATUS="${YELLOW}⚠  status unknown${RESET}"
    elif echo "$result" | grep -qi "moov not found\|missing moov"; then
        FILE_STATUS="${YELLOW}⚠  moov atom not found${RESET}"
    elif echo "$result" | grep -qi "corrupt\|error"; then
        FILE_STATUS="${RED}✗  file corrupted${RESET}"
    else
        FILE_STATUS="${GREEN}✓  file OK${RESET}"
    fi
}

file_browser() {
    local current_dir="${1:-$HOME}"

    while true; do
        clear
        echo ""
        echo -e " ${CYAN}${BOLD}kythera-core${RESET} ${GRAY}/ file browser${RESET}"
        echo -e "$DIVIDER"
        echo ""
        echo -e " ${GRAY}location:${RESET} ${WHITE}$current_dir${RESET}"
        echo ""

        local entries=()
        local display=()

        if [[ "$current_dir" != "/" ]]; then
            entries+=("__UP__")
            display+=("${GRAY}..  (up)${RESET}")
        fi

        while IFS= read -r d; do
            [[ -z "$d" ]] && continue
            entries+=("$d")
            display+=("${CYAN}$(basename "$d")/${RESET}")
        done < <(find "$current_dir" -maxdepth 1 -mindepth 1 -type d ! -name '.*' | sort)

        local mp4_count=0
        while IFS= read -r f; do
            [[ -z "$f" ]] && continue
            local size
            size=$(du -h "$f" 2>/dev/null | cut -f1)
            entries+=("$f")
            display+=("${WHITE}$(basename "$f")${RESET}  ${GRAY}$size${RESET}")
            (( mp4_count++ ))
        done < <(find "$current_dir" -maxdepth 1 -mindepth 1 -type f -iname '*.mp4' | sort)

        local total=${#entries[@]}
        if [[ $total -eq 0 ]] || ( [[ $total -eq 1 ]] && [[ "${entries[0]}" == "__UP__" ]] && [[ $mp4_count -eq 0 ]] ); then
            echo -e " ${GRAY}(folder kosong / tidak ada file MP4)${RESET}"
        else
            for i in "${!entries[@]}"; do
                local num=$(( i + 1 ))
                printf " ${GRAY}%2d${RESET}  %b\n" "$num" "${display[$i]}"
            done
        fi

        echo ""
        echo -e "$DIVIDER"
        echo -e " ${GRAY}ketik nomor untuk pilih, atau:${RESET}"
        echo -e "  ${WHITE}p${RESET}  ${GRAY}masukkan path manual${RESET}"
        echo -e "  ${WHITE}s${RESET}  ${GRAY}storage Android (/storage/emulated/0)${RESET}"
        echo -e "  ${WHITE}h${RESET}  ${GRAY}home Termux (~)${RESET}"
        echo -e "  ${WHITE}0${RESET}  ${GRAY}batal / kembali${RESET}"
        echo ""
        echo -e "$DIVIDER"
        echo -ne " ${CYAN}>${RESET} "
        read -r sel

        case "$sel" in
            0)
                return 1
                ;;
            p|P)
                echo ""
                echo -e " ${GRAY}masukkan path lengkap file MP4:${RESET}"
                echo -ne " ${CYAN}>${RESET} "
                read -r raw_path
                raw_path="${raw_path//\'/}"
                raw_path="${raw_path//\"/}"
                raw_path="${raw_path/#\~/$HOME}"
                raw_path="$(echo "$raw_path" | xargs)"
                if [[ -f "$raw_path" ]]; then
                    SELECTED_FILE="$raw_path"
                    echo -e " ${GREEN}✓${RESET} loaded: ${WHITE}$(basename "$raw_path")${RESET}"
                    sleep 1
                    return 0
                else
                    echo -e " ${RED}✗${RESET} file tidak ditemukan"
                    sleep 1
                fi
                ;;
            s|S)
                current_dir="/storage/emulated/0"
                ;;
            h|H)
                current_dir="$HOME"
                ;;
            ''|*[!0-9]*)
                echo -e " ${RED}✗${RESET} input tidak valid"
                sleep 1
                ;;
            *)
                local idx=$(( sel - 1 ))
                if [[ $idx -lt 0 ]] || [[ $idx -ge $total ]]; then
                    echo -e " ${RED}✗${RESET} nomor tidak ada"
                    sleep 1
                    continue
                fi

                local picked="${entries[$idx]}"

                if [[ "$picked" == "__UP__" ]]; then
                    current_dir="$(dirname "$current_dir")"
                elif [[ -d "$picked" ]]; then
                    current_dir="$picked"
                elif [[ -f "$picked" ]]; then
                    SELECTED_FILE="$picked"
                    echo ""
                    echo -e " ${GREEN}✓${RESET} loaded: ${WHITE}$(basename "$picked")${RESET}"
                    echo -e "   ${GRAY}$(du -h "$picked" | cut -f1) · $picked${RESET}"
                    sleep 1
                    return 0
                fi
                ;;
        esac
    done
}

show_ui() {
    clear
    local fname="${GRAY}no file loaded${RESET}"
    if [[ -n "$SELECTED_FILE" ]]; then
        fname="${WHITE}$(basename "$SELECTED_FILE")${RESET}  ${GRAY}$(du -h "$SELECTED_FILE" | cut -f1)${RESET}"
    fi

    echo ""
    echo -e " ${CYAN}${BOLD}kythera-core v2.1.0${RESET}"
    echo -e "$DIVIDER"
    echo ""
    echo -e " ${GRAY}session:${RESET} $SESSION_TIME"
    echo -e " ${GRAY}target: ${RESET}  $fname"
    echo -e " ${GRAY}status: ${RESET}  $FILE_STATUS"
    echo ""
    echo -e "$DIVIDER"
    echo ""
    echo -e "  ${CYAN}1${RESET}  ${WHITE}Scan structure${RESET}"
    echo -e "  ${CYAN}2${RESET}  ${WHITE}Detect moov/mvhd${RESET}"
    echo -e "  ${CYAN}3${RESET}  ${WHITE}Repair moov${RESET}"
    echo -e "  ${CYAN}4${RESET}  ${WHITE}Patch mvhd byte${RESET}              ${CYAN}[primary]${RESET}"
    echo -e "  ${CYAN}5${RESET}  ${WHITE}Analyze metadata${RESET}"
    echo -e "  ${CYAN}6${RESET}  ${WHITE}Faststart optimizer${RESET}"
    echo -e "  ${CYAN}7${RESET}  ${WHITE}Check corruption${RESET}"
    echo -e "  ${CYAN}8${RESET}  ${WHITE}Export report${RESET}"
    echo ""
    echo -e "  ${GRAY}f  change file${RESET}"
    echo -e "  ${GRAY}0  exit${RESET}"
    echo ""
    echo -e "$DIVIDER"
    echo -ne " ${CYAN}>${RESET} "
}

check_deps() {
    local ok=1
    if ! command -v python3 &>/dev/null; then
        echo -e " ${RED}✗${RESET} python3 not found — run: pkg install python"
        ok=0
    fi
    if [[ ! -f "$CORE_PY" ]]; then
        echo -e " ${RED}✗${RESET} core.py not found in: $SCRIPT_DIR"
        ok=0
    fi
    [[ $ok -eq 1 ]]
}

run_core() {
    local menu_num="$1"
    local filepath="$2"
    echo ""
    echo -e "$DIVIDER"
    python3 "$CORE_PY" "$menu_num" "$filepath"
    local rc=$?
    echo -e "$DIVIDER"
    if [[ $rc -eq 0 ]]; then
        echo -e " ${GREEN}✓${RESET} done"
    else
        echo -e " ${RED}✗${RESET} exited with code $rc"
    fi
}

pause_continue() {
    echo ""
    echo -e " ${GRAY}press Enter to continue...${RESET}"
    read -r
}

handle_menu() {
    local choice="$1"
    local label="$2"

    if [[ -z "$SELECTED_FILE" ]]; then
        echo ""
        echo -e " ${YELLOW}⚠${RESET}  no file loaded"
        pause_continue
        return
    fi

    echo ""
    echo -e " ${GRAY}running:${RESET} ${WHITE}$label${RESET}"

    if [[ "$choice" == "4" ]]; then
        echo -e " ${YELLOW}⚠${RESET}  auto-backup (.bak) will be created"
    elif [[ "$choice" == "6" ]]; then
        echo -e " ${GRAY}   output: *_faststart.mp4${RESET}"
    fi

    run_core "$choice" "$SELECTED_FILE"
    update_file_status "$SELECTED_FILE"
    pause_continue
}

main() {
    if ! check_deps; then
        echo ""
        exit 1
    fi

    clear
    echo ""
    echo -e " ${CYAN}${BOLD}kythera-core v2.1.0${RESET}"
    echo -e "$DIVIDER"
    echo ""
    echo -e " ${GRAY}selamat datang. pilih file MP4 untuk memulai.${RESET}"
    echo ""
    echo -e " ${GRAY}press Enter untuk buka file browser...${RESET}"
    read -r

    if ! file_browser "$HOME"; then
        clear
        echo ""
        echo -e " ${GRAY}kythera-core — session ended${RESET}"
        echo ""
        exit 0
    fi

    update_file_status "$SELECTED_FILE"

    while true; do
        show_ui
        read -r choice

        case "$choice" in
            0)
                clear
                echo ""
                echo -e " ${GRAY}kythera-core — session ended${RESET}"
                echo ""
                exit 0
                ;;
            f|F)
                file_browser "$HOME"
                update_file_status "$SELECTED_FILE"
                ;;
            1) handle_menu "1" "scan structure" ;;
            2) handle_menu "2" "detect moov/mvhd" ;;
            3) handle_menu "3" "repair moov" ;;
            4) handle_menu "4" "patch mvhd byte" ;;
            5) handle_menu "5" "analyze metadata" ;;
            6) handle_menu "6" "faststart optimizer" ;;
            7) handle_menu "7" "check corruption" ;;
            8) handle_menu "8" "export report" ;;
            "") ;;
            *)
                echo -e "\n ${RED}✗${RESET} invalid: '$choice'"
                sleep 1
                ;;
        esac
    done
}

main
