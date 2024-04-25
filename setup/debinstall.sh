#!/bin/sh
#
# Install Debian packages needed to run Odoo.


if [ "$1" = "-l" -o "$1" = "--list" ]; then
    cmd="echo"
else
    cmd="apt-get install -y --no-install-recommends"
    if [ "$(id -u)" -ne "0" ]; then
        echo "\033[0;31mThis script must be run as root to install dependencies, starting a dry run.\033[0m" >&2
        cmd="$cmd -s"
    else
        apt-get update
    fi
    if [ "$1" = "-q" -o "$1" = "--quiet" ]; then
        cmd="$cmd -qq"
    fi
fi

script_path=$(realpath "$0")
script_dir=$(dirname "$script_path")
control_path=$(realpath "$script_dir/../debian/control")

sed -n '/^Depends:/,/^[A-Z]/p' "$control_path" \
| awk '/^ [a-z]/ { gsub(/,/,"") ; gsub(" ", "") ; print $NF }' | sort -u \
| DEBIAN_FRONTEND=noninteractive xargs $cmd
