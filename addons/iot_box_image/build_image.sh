#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

file_exists() {
    [[ -f $1 ]];
}

require_command () {
    type "$1" &> /dev/null || { echo "Command $1 is missing. Install it e.g. with 'apt-get install $1'. Aborting." >&2; exit 1; }
}

require_command kpartx
require_command qemu-arm-static
require_command zerofree

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
__file="${__dir}/$(basename "${BASH_SOURCE[0]}")"
__base="$(basename ${__file} .sh)"

MOUNT_POINT="${__dir}/root_mount"
OVERWRITE_FILES_BEFORE_INIT_DIR="${__dir}/overwrite_before_init"
OVERWRITE_FILES_AFTER_INIT_DIR="${__dir}/overwrite_after_init"
VERSION=17.0
VERSION_IOTBOX=24.10

if [[ "${1:-}" == "-c" || "${1:-}" == "--cleanup" ]]; then
    echo "Cleaning up..."
    umount -fv "${MOUNT_POINT}/boot/" > /dev/null 2>&1 || true
    umount -lv "${MOUNT_POINT}/" > /dev/null 2>&1 || true
    rm -rfv "${MOUNT_POINT}"
    rm -rf overwrite_before_init/usr
    rm -rf overwrite_before_init/home/pi/odoo
    rm -rfv iotbox.img
    sudo kpartx -d /dev/loop1 > /dev/null 2>&1 || true
    losetup -d /dev/loop1 > /dev/null 2>&1 || true
    echo "Cleanup done."
    exit 0
fi

# ask user for the branch/version
current_branch="$(git branch --show-current)"
read -p "Enter dev branch [${current_branch}]: " VERSION
VERSION=${VERSION:-$current_branch}

# ask user for the repository
current_remote=$(git config branch.$current_branch.remote)
current_repo="$(git remote get-url $current_remote | sed 's/.*github.com[\/:]//' | sed 's/\/odoo.git//')"
read -p "Enter repo [${current_repo}]: " REPO
REPO="https://github.com/${REPO:-$current_repo}/odoo.git"
echo "Using repo: ${REPO}"

if ! file_exists *raspios*.img ; then
    wget "https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2024-10-28/2024-10-22-raspios-bookworm-armhf-lite.img.xz" -O raspios.img.xz
    unxz --verbose raspios.img.xz
fi

RASPIOS=$(echo *raspios*.img)
rsync -avh --progress "${RASPIOS}" iotbox.img

CLONE_DIR="${OVERWRITE_FILES_BEFORE_INIT_DIR}/home/pi/odoo"

rm -rfv "${CLONE_DIR}"

if [ ! -d $CLONE_DIR ]; then
    echo "Clone Github repo"
    mkdir -pv "${CLONE_DIR}"
    git clone -b ${VERSION} --no-local --no-checkout --depth 1 ${REPO} "${CLONE_DIR}"
    cd "${CLONE_DIR}"
    git config core.sparsecheckout true
    echo "addons/web
addons/hw_*
addons/iot_box_image/configuration
addons/point_of_sale/tools/posbox/configuration
odoo/
odoo-bin" | tee --append .git/info/sparse-checkout > /dev/null
    git read-tree -mu HEAD
    git remote set-url origin "https://github.com/odoo/odoo.git" # ensure remote is the original repo
fi

cd "${__dir}"
USR_BIN="${OVERWRITE_FILES_BEFORE_INIT_DIR}/usr/bin/"
mkdir -pv "${USR_BIN}"
cd "/tmp"
curl 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm.tgz' > ngrok.tgz
tar xvzf ngrok.tgz -C "${USR_BIN}"
rm -v ngrok.tgz
cd "${__dir}"

# zero pad the image to be around ~5 GiB, by default the image is only ~2.2 GiB
echo "Enlarging the image..."
dd if=/dev/zero bs=1M count=2560 status=progress >> iotbox.img

# resize partition table
echo "Fdisking"

SECTORS_BOOT_START=$(sudo fdisk -l iotbox.img | tail -n 2 | awk 'NR==1 {print $2}')
SECTORS_BOOT_END=$((SECTORS_BOOT_START + 1056767)) # sectors to have a partition of ~512Mo
SECTORS_ROOT_START=$((SECTORS_BOOT_END + 1))

(echo 'p';                          # print
 echo 'd';                          # delete
 echo '2';                          #    number 2
 echo 'd';                          # delete number 1 by default
 echo 'n';                          # create new partition
 echo 'p';                          #   primary
 echo '1';                          #   number 1
 echo "${SECTORS_BOOT_START}";      #   first sector
 echo "${SECTORS_BOOT_END}";        #   partition size
 echo 't';                          # change type of partition. 1 selected by default
 echo 'c';                          #   change to W95 FAT32 (LBA)
 echo 'n';                          # create new partition
 echo 'p';                          #   primary
 echo '2';                          #   number 2
 echo "${SECTORS_ROOT_START}";      #   starting at previous offset
 echo '';                           #   ending at default (fdisk should propose max)
 echo 'p';                          # print
 echo 'w') | fdisk iotbox.img       # write and quit

LOOP_RASPIOS=$(kpartx -avs "${RASPIOS}")
LOOP_RASPIOS_ROOT=$(echo "${LOOP_RASPIOS}" | tail -n 1 | awk '{print $3}')
LOOP_RASPIOS_PATH="/dev/${LOOP_RASPIOS_ROOT::-2}"
LOOP_RASPIOS_ROOT="/dev/mapper/${LOOP_RASPIOS_ROOT}"
LOOP_RASPIOS_BOOT=$(echo "${LOOP_RASPIOS}" | head -n 1 | awk '{print $3}')
LOOP_RASPIOS_BOOT="/dev/mapper/${LOOP_RASPIOS_BOOT}"

LOOP_IOT=$(kpartx -avs iotbox.img)
LOOP_IOT_ROOT=$(echo "${LOOP_IOT}" | tail -n 1 | awk '{print $3}')
LOOP_IOT_PATH="/dev/${LOOP_IOT_ROOT::-2}"
LOOP_IOT_ROOT="/dev/mapper/${LOOP_IOT_ROOT}"
LOOP_IOT_BOOT=$(echo "${LOOP_IOT}" | head -n 1 | awk 'NR==1 {print $3}')
LOOP_IOT_BOOT="/dev/mapper/${LOOP_IOT_BOOT}"

mkfs.ext4 -v "${LOOP_IOT_ROOT}"

dd if="${LOOP_RASPIOS_ROOT}" of="${LOOP_IOT_ROOT}" bs=4M status=progress

# resize filesystem
e2fsck -fvy "${LOOP_IOT_ROOT}" # resize2fs requires clean fs
resize2fs "${LOOP_IOT_ROOT}"

mkdir -pv "${MOUNT_POINT}" #-p: no error if existing
mount -v "${LOOP_IOT_ROOT}" "${MOUNT_POINT}"
mount -v "${LOOP_IOT_BOOT}" "${MOUNT_POINT}/boot/"

QEMU_ARM_STATIC="/usr/bin/qemu-arm-static"
cp -v "${QEMU_ARM_STATIC}" "${MOUNT_POINT}/usr/bin/"

# 'overlay' the overwrite directory onto the mounted image filesystem
cp -av "${OVERWRITE_FILES_BEFORE_INIT_DIR}"/* "${MOUNT_POINT}"

# Reload network manager is mandatory in order to apply DNS configurations:
# it needs to be reloaded after copying the 'overwrite_before_init' files in the new image
# it needs to be performed in the classic filesystem, as 'systemctl' commands are not available in /root_bypass_ramdisks
sudo systemctl reload NetworkManager

chroot "${MOUNT_POINT}" /bin/bash -c "/etc/init_image.sh"

# copy iotbox version
mkdir -pv "${MOUNT_POINT}"/var/odoo/
echo "${VERSION_IOTBOX}" > "${MOUNT_POINT}"/var/odoo/iotbox_version

# get rid of the git clone
rm -rf "${CLONE_DIR}"
# and the ngrok usr/bin
rm -rf "${OVERWRITE_FILES_BEFORE_INIT_DIR}/usr"
cp -a "${OVERWRITE_FILES_AFTER_INIT_DIR}"/* "${MOUNT_POINT}"

find "${MOUNT_POINT}"/ -type f -name "*.iotpatch"|while read iotpatch; do
    DIR=$(dirname "${iotpatch}")
    BASE=$(basename "${iotpatch%.iotpatch}")
    find "${DIR}" -type f -name "${BASE}" ! -name "*.iotpatch"|while read file; do
        patch -f --verbose "${file}" < "${iotpatch}"
    done
done

# cleanup
umount -fv "${MOUNT_POINT}"/boot/
umount -lv "${MOUNT_POINT}"/
rm -rfv "${MOUNT_POINT}"
kpartx -dv "${LOOP_IOT_PATH}"  # /dev/loop1
losetup -d "${LOOP_IOT_PATH}"  # /dev/loop1

echo "Running zerofree..."
zerofree -v "${LOOP_IOT_ROOT}" || true

sleep 10

kpartx -dv "${LOOP_IOT_PATH}"
kpartx -dv "${LOOP_RASPIOS_PATH}"

echo "Image build finished."
