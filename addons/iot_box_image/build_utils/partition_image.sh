#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

ensure_root # Check if script is run as root, exit if not

require_command fdisk
require_command losetup
require_command parted
require_command qemu-arm-static

IOTBOX=$1
PICORE=$2
RASPIOS=$3

# Enlarge the image (zero-pad). Sector size is 512 bytes (checked with: sudo fdisk -l raspios.img).
# We want to add 2.75GiB to the system partition to have enough space to install programs:
# x (MiB) * 1024 * 1024 / 512 = y (sectors) <=> x (GiB) * 2048 = y (sectors)
# e.g.  (2.75 * 1024)MiB * 2048 = 5.5M (sectors)
# We want to add enough space for the recovery partition (piCore): we add as much space as the piCore system partition.
echo "Enlarging the image..."
SYSTEM_INCREASE_MiB=2816 # 2.75GiB * 1024 = 2816MiB, using MiB to avoid floating numbers
SYSTEM_INCREASE_AMOUNT_SECTORS=$((SYSTEM_INCREASE_MiB * 2048)) # sectors
PICORE_SYSTEM_AMOUNT_SECTORS=$(fdisk -l ${PICORE} | awk 'END {print $4}')
PICORE_SYSTEM_AMOUNT_SECTORS=$((PICORE_SYSTEM_AMOUNT_SECTORS + 20480)) # add 10MiB * 1024 * 1024 / 512 = 20480 sectors (to store upgrade scripts)

TOTAL_INCREASE=$((SYSTEM_INCREASE_AMOUNT_SECTORS + PICORE_SYSTEM_AMOUNT_SECTORS))
dd if=/dev/zero of=./iotbox.img bs=512 count=${TOTAL_INCREASE} status=progress conv=notrunc oflag=append

# Map partitions from the Raspberry Pi OS image to loop devices (/dev/mappers/loop0pX).
LOOP_RASPIOS=$(losetup -Pf --show ${RASPIOS})
LOOP_RASPIOS_SYS="/dev/${LOOP_RASPIOS}p2" # /dev/loop0p2
echo "Loop devices for ${RASPIOS}:"
echo "  System: ${LOOP_RASPIOS_SYS}"

# Map partitions from the IoT Box image to loop devices (/dev/mappers/loop1pX).
LOOP_IOT=$(losetup -Pf --show ${IOTBOX})
LOOP_IOT_BOOT="/dev/${LOOP_IOT}p1)" # /dev/loop1p1
LOOP_IOT_SYS="/dev/${LOOP_IOT}p2" # /dev/loop1p2
echo "Loop devices for ${IOTBOX}:"
echo "  Boot: ${LOOP_IOT_BOOT}"
echo "  System: ${LOOP_IOT_SYS}"

# Map partitions from the piCore image to loop devices (/dev/mappers/loop2pX).
LOOP_PICORE=$(losetup -Pf --show ${PICORE})
LOOP_PICORE_SYS="/dev/${LOOP_PICORE}p2)" # /dev/loop2p2
echo "Loop devices for ${PICORE}:"
echo "  System: ${LOOP_PICORE_SYS}"

# Get the current size of the system partition.
SYSTEM_AMOUNT_SECTORS=$(fdisk -l ${IOTBOX} | grep "${IOTBOX}2" | awk '{print $4}')

# Resize the system partition to make it smaller (make it recovery partition: piCore).
SYSTEM_FIRST_SECTOR=$(fdisk -l ${IOTBOX} | grep "${IOTBOX}2" | awk '{print $2}')
NEW_END_SECTOR_RECOVERY=$((SYSTEM_FIRST_SECTOR + PICORE_SYSTEM_AMOUNT_SECTORS - 1))
parted -s ${LOOP_IOT} rm 2
parted -s ${LOOP_IOT} mkpart primary ext4 "${SYSTEM_FIRST_SECTOR}s" "${NEW_END_SECTOR_RECOVERY}s"

# We want to create a new partition for the system
# We then take the last sector of the image, and add raspbian system's amount of sectors to it
START_SECTOR_SYSTEM=$((NEW_END_SECTOR_RECOVERY + 1))
END_SECTOR_SYSTEM=$((START_SECTOR_SYSTEM + SYSTEM_AMOUNT_SECTORS + SYSTEM_INCREASE_AMOUNT_SECTORS - 1))
parted -s ${LOOP_IOT} mkpart primary ext4 "${START_SECTOR_SYSTEM}s" "${END_SECTOR_SYSTEM}s"

# We need to map the new partition to a loop device (we remap the whole image).
# This remapping will also allow us to resize the filesystem, taking changes into account.
losetup -d ${IOTBOX}
LOOP_IOT=$(losetup -Pf --show ${IOTBOX})
LOOP_IOT_BOOT="/dev/${LOOP_IOT}p1" # /dev/loop1p1
LOOP_IOT_RECOVERY="/dev/${LOOP_IOT}p2" # /dev/loop1p2
LOOP_IOT_SYS="/dev/${LOOP_IOT}p3" # /dev/loop1p3

# Format and resize recovery partition filesystem.
mkfs.ext4 -F ${LOOP_IOT_RECOVERY}
e2fsck -fvy ${LOOP_IOT_RECOVERY}
resize2fs ${LOOP_IOT_RECOVERY}

# Clone the piCore system into the recovery partition.
echo "Installing Tiny Core (piCore) into the recovery partition..."
dd if=${LOOP_PICORE_SYS} of=${LOOP_IOT_RECOVERY} bs=512 status=progress

# Format system partition.
mkfs.ext4 -F ${LOOP_IOT_SYS}

# Clone the Raspberry Pi OS image into the IoT Box image.
echo "Installing Raspberry Pi OS into the system partition..."
dd if=${LOOP_RASPIOS_SYS} of=${LOOP_IOT_SYS} bs=512 status=progress

# As dd copied a ~2.2GB partition inside our 4.4GB one, we need to resize its filesystem
# to take the whole space into account.
e2fsck -fvy ${LOOP_IOT_SYS}
resize2fs ${LOOP_IOT_SYS}

# Label the partitions.
e2label ${LOOP_IOT_SYS} iotboxfs
e2label ${LOOP_IOT_RECOVERY} picorefs
