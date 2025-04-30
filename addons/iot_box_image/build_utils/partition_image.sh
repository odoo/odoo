#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

ensure_root # Check if script is run as root, exit if not

require_command fdisk
require_command losetup
require_command parted
require_command e2fsck
require_command resize2fs
require_command e2label

IOTBOX=$1

# Enlarge the image (zero-pad). Sector size is 512 bytes (checked with: sudo fdisk -l raspios.img).
# Note that we can dd using bigger sector size to speed up the process, but we need to be careful with the amount of sectors.
#
# We want to add 2.75GiB to the system partition to have enough space to install programs:
# x (MiB) * 1024 * 1024 / 512 = y (sectors) <=> x (GiB) * 2048 = y (sectors)
# e.g.  (2.75 * 1024) MiB * 2048 = 5.5M (sectors)
echo "Enlarging the image..."
SYSTEM_INCREASE_MiB=2816 # 2.75GiB * 1024 = 2816MiB, using MiB to avoid floating numbers
SYSTEM_INCREASE_AMOUNT_SECTORS=$((SYSTEM_INCREASE_MiB * 2048)) # sectors
dd if=/dev/zero of="./${IOTBOX}" bs=512 count=${SYSTEM_INCREASE_AMOUNT_SECTORS} status=progress conv=notrunc oflag=append

# Map partitions from the IoT Box image to loop devices (/dev/loop1pX).
LOOP_IOT=$(losetup -Pf --show ${IOTBOX})
LOOP_IOT_BOOT="${LOOP_IOT}p1)" # /dev/loop1p1
LOOP_IOT_SYS="${LOOP_IOT}p2" # /dev/loop1p2
echo "Loop devices for ${IOTBOX}:"
echo "  Boot: ${LOOP_IOT_BOOT}"
echo "  System: ${LOOP_IOT_SYS}"

# Resize the system partition to make it bigger:
# We take the last sector of the raspbian image, and add the amount of sectors of the increase (gives us the end sector).
SYSTEM_END_SECTOR=$(fdisk -l ${IOTBOX} | grep "${IOTBOX}2" | awk '{print $3}')
NEW_END_SECTOR_SYSTEM=$((SYSTEM_END_SECTOR + SYSTEM_INCREASE_AMOUNT_SECTORS - 1))
parted -s ${LOOP_IOT} resizepart 2 "${NEW_END_SECTOR_SYSTEM}s"

# We need to remap the whole image to resize the filesystem taking changes into account.
losetup -d ${LOOP_IOT}
LOOP_IOT=$(losetup -Pf --show ${IOTBOX})
LOOP_IOT_BOOT="${LOOP_IOT}p1" # /dev/loop1p1
LOOP_IOT_SYS="${LOOP_IOT}p2" # /dev/loop1p2

# Format and resize system partition filesystem.
e2fsck -fvy ${LOOP_IOT_SYS}
resize2fs ${LOOP_IOT_SYS}

# Rename the system partition (optional but cool).
e2label ${LOOP_IOT_SYS} iotboxfs
