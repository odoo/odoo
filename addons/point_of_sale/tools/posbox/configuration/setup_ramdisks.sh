#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace

create_ramdisk () {
    ORIGINAL="${1}"
    RAMDISK="${ORIGINAL}_ram"
    SIZE="${2}"
    echo "Creating ramdisk for ${1} of size ${SIZE}..."

    mount -t tmpfs -o size="${SIZE}" tmpfs "${RAMDISK}"
    rsync -a --exclude="swap" --exclude="apt" --exclude="dpkg" --exclude=".mozilla" "${ORIGINAL}/" "${RAMDISK}/"
    mount --bind "${RAMDISK}" "${ORIGINAL}"
}

echo "Creating ramdisks..."
create_ramdisk "/var" "192M"
create_ramdisk "/etc" "16M"
create_ramdisk "/tmp" "64M"

# bind mount / so that we can get to the real /var and /etc
mount --bind / /root_bypass_ramdisks

# allow to cups server to save configuration file of printers
mount --bind /root_bypass_ramdisks/etc/cups /root_bypass_ramdisks/etc/cups
mount -o remount,rw /root_bypass_ramdisks/etc/cups /root_bypass_ramdisks/etc/cups
