#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -t 0 ] || [ ! -t 1 ]; then
    echo "[make-tui] This menu requires an interactive terminal."
    exit 1
fi

collect_targets() {
    make help | awk '
        /^[A-Za-z][A-Za-z0-9 \/&()-]*:$/ {
            section = $0
            sub(/:$/, "", section)
            next
        }
        /^  make / {
            line = $0
            sub(/^  make /, "", line)
            split(line, parts, /[[:space:]]*# /)
            target = parts[1]
            desc = parts[2]
            if (section == "Targets" || section == "Examples") {
                section = "General"
            }
            print target "\t" section "\t" desc
        }
    '
}

run_target() {
    local target="$1"
    if [ -z "$target" ]; then
        exit 0
    fi
    echo "[make-tui] Running: make $target"
    exec make "$target"
}

menu_with_fzf() {
    local selection target
    selection="$(
        collect_targets | fzf \
            --delimiter=$'\t' \
            --with-nth=2,1,3 \
            --prompt='make > ' \
            --height=85% \
            --layout=reverse \
            --border \
            --header=$'Section\tTarget\tDescription\nEnter: run target | Esc: cancel'
    )" || exit 0
    target="${selection%%$'\t'*}"
    run_target "$target"
}

menu_with_whiptail() {
    local -a options=()
    local target section desc choice
    while IFS=$'\t' read -r target section desc; do
        options+=("$target" "[$section] $desc")
    done < <(collect_targets)

    if [ "${#options[@]}" -eq 0 ]; then
        echo "[make-tui] No targets found in make help."
        exit 1
    fi

    choice="$(
        whiptail \
            --title "Kodoo Make TUI" \
            --menu "Select a Make target" \
            24 100 14 \
            "${options[@]}" \
            3>&1 1>&2 2>&3
    )" || exit 0

    run_target "$choice"
}

menu_with_select() {
    local -a targets=()
    local -a sections=()
    local -a descriptions=()
    local line target section desc choice current_section=""

    while IFS=$'\t' read -r target section desc; do
        targets+=("$target")
        sections+=("$section")
        descriptions+=("$desc")
    done < <(collect_targets)

    if [ "${#targets[@]}" -eq 0 ]; then
        echo "[make-tui] No targets found in make help."
        exit 1
    fi

    echo "Kodoo Make TUI"
    echo
    for i in "${!targets[@]}"; do
        if [ "${sections[$i]}" != "$current_section" ]; then
            current_section="${sections[$i]}"
            printf "\n[%s]\n" "$current_section"
        fi
        printf "%2d) %-24s %s\n" "$((i + 1))" "${targets[$i]}" "${descriptions[$i]}"
    done
    echo " 0) exit"
    echo

    while true; do
        printf "Target number: "
        read -r choice
        if [ "$choice" = "0" ]; then
            exit 0
        fi
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#targets[@]}" ]; then
            run_target "${targets[$((choice - 1))]}"
        fi
        echo "Invalid choice."
    done
}

if command -v fzf >/dev/null 2>&1; then
    menu_with_fzf
elif command -v whiptail >/dev/null 2>&1; then
    menu_with_whiptail
else
    menu_with_select
fi
