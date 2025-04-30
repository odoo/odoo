#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

ensure_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "This script must be run as root"
        exit 1
    fi
}

file_exists() {
    [[ -f $1 ]];
}

require_command() {
    type "$1" &> /dev/null || {
      echo "Command $1 is missing. Install it (e.g. with 'apt-get install $1'). Aborting." >&2;
      exit 1;
    }
}
