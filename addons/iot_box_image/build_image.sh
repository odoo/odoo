#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
__file="${__dir}/$(basename "${BASH_SOURCE[0]}")"
__base="$(basename ${__file} .sh)"

source ${__dir}/configuration/image_utils.sh # Load useful functions

ensure_root # Check if script is run as root, exit if not

# Require tools
require_command kpartx
require_command losetup
require_command zerofree

# Define mount points and directories
MOUNT_POINT="${__dir}/root_mount"
RECOVERY_MOUNT="${__dir}/recovery_mount"
OVERWRITE_FILES_BEFORE_INIT_DIR="${__dir}/overwrite_before_init"
OVERWRITE_FILES_AFTER_INIT_DIR="${__dir}/overwrite_after_init"
BUILD_UTILS_DIR="${__dir}/build_utils"
VERSION_IOTBOX="$(date '+%y.%m')"

if [[ "${1:-}" == "-c" || "${1:-}" == "--cleanup" ]]; then
    echo "Cleaning up..."
    umount -fv "${MOUNT_POINT}/boot/" > /dev/null 2>&1 || true
    umount -lv "${MOUNT_POINT}" > /dev/null 2>&1 || true
    rm -rfv "${MOUNT_POINT}"
    rm -rf overwrite_before_init/usr
    rm -rf overwrite_before_init/home/pi/odoo
    rm -rfv iotbox.img
    sudo kpartx -d /dev/loop1 > /dev/null 2>&1 || true
    losetup -d /dev/loop1 > /dev/null 2>&1 || true
    sudo kpartx -d /dev/loop0 > /dev/null 2>&1 || true
    losetup -d /dev/loop0 > /dev/null 2>&1 || true
    echo "Cleanup done."
    exit 0
fi

# Download and extract Raspberry Pi OS, piCore, ngrok and clone Odoo repository
source ${BUILD_UTILS_DIR}/download_requirements.sh "${__dir}"

# Clone the Raspberry Pi OS image into the IoT Box image.
rsync -avh --progress "${RASPIOS}" iotbox.img

# Prepare the image for the IoT Box system: partition and format.
# source to share variables
source ${BUILD_UTILS_DIR}/partition_image.sh "iotbox.img" "${PICORE}" "${RASPIOS}"

# Mount system partition and customize the active system
mkdir -pv "${MOUNT_POINT}"
mount -v "${LOOP_IOT_SYS}" "${MOUNT_POINT}"
mount -v "${LOOP_IOT_BOOT}" "${MOUNT_POINT}/boot/"

# Set iotboxfs as the partition to boot on.
change_boot_priority ${LOOP_IOT_RECOVERY} ${LOOP_IOT_SYS} "${MOUNT_POINT}/boot"

QEMU_ARM_STATIC="/usr/bin/qemu-arm-static"
cp -v "${QEMU_ARM_STATIC}" "${MOUNT_POINT}/usr/bin/"

# 'Overlay' the pre-init overwrite directory onto the mounted image filesystem.
cp -av "${OVERWRITE_FILES_BEFORE_INIT_DIR}"/* "${MOUNT_POINT}"

# Reload network manager is mandatory in order to apply DNS configurations:
# it needs to be reloaded after copying the 'overwrite_before_init' files in the new image
# it needs to be performed in the classic filesystem, as 'systemctl' commands are not available in /root_bypass_ramdisks
sudo systemctl reload NetworkManager

# Run initialization script inside /mount_point (the mounted path of the image)
chroot "${MOUNT_POINT}" /bin/bash -c "/etc/init_image.sh"

# Copy IoT Box version info.
mkdir -pv "${MOUNT_POINT}/var/odoo/"
echo "${VERSION_IOTBOX}" > "${MOUNT_POINT}/var/odoo/iotbox_version"

# 'Overlay' the post-init overwrite directory onto the mounted image filesystem.
cp -a "${OVERWRITE_FILES_AFTER_INIT_DIR}"/* "${MOUNT_POINT}"

echo "Running zerofree..."
zerofree -v "${LOOP_IOT_SYS}" || true

sleep 10

# Final cleanup: unmount partitions and remove loop device mappings
rm -rf "${CLONE_DIR}"
rm -rf "${OVERWRITE_FILES_BEFORE_INIT_DIR}/usr"
umount -fv "${MOUNT_POINT}"/boot/
umount -lv "${MOUNT_POINT}"/
rm -rfv "${MOUNT_POINT}"
kpartx -dv iotbox.img
kpartx -dv "${PICORE}"

echo "Image build finished."
