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
VERSION=13.0
REPO=https://github.com/odoo/odoo.git

if ! file_exists *raspbian*.img ; then
    wget 'http://downloads.raspberrypi.org/raspbian_lite/images/raspbian_lite-2019-09-30/2019-09-26-raspbian-buster-lite.zip' -O raspbian.img.zip
    unzip raspbian.img.zip
fi

cp -a *raspbian*.img iotbox.img

CLONE_DIR="${OVERWRITE_FILES_BEFORE_INIT_DIR}/home/pi/odoo"

rm -rf "${CLONE_DIR}"

if [ ! -d $CLONE_DIR ]; then
    echo "Clone Github repo"
    mkdir -p "${CLONE_DIR}"
    git clone -b ${VERSION} --no-local --no-checkout --depth 1 ${REPO} "${CLONE_DIR}"
    cd "${CLONE_DIR}"
    git config core.sparsecheckout true
    echo "addons/web
addons/hw_*
addons/point_of_sale/tools/posbox/configuration
odoo/
odoo-bin" | tee --append .git/info/sparse-checkout > /dev/null
    git read-tree -mu HEAD
fi

cd "${__dir}"
USR_BIN="${OVERWRITE_FILES_BEFORE_INIT_DIR}/usr/bin/"
mkdir -p "${USR_BIN}"
cd "/tmp"
curl 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm.zip' > ngrok.zip
unzip ngrok.zip
rm ngrok.zip
cd "${__dir}"
mv /tmp/ngrok "${USR_BIN}"

# zero pad the image to be around 3.5 GiB, by default the image is only ~1.3 GiB
echo "Enlarging the image..."
dd if=/dev/zero bs=1M count=2048 >> iotbox.img

# resize partition table
echo "Fdisking"
START_OF_ROOT_PARTITION=$(fdisk -l iotbox.img | tail -n 1 | awk '{print $2}')
(echo 'p';                          # print
 echo 'd';                          # delete
 echo '2';                          #   second partition
 echo 'n';                          # create new partition
 echo 'p';                          #   primary
 echo '2';                          #   number 2
 echo "${START_OF_ROOT_PARTITION}"; #   starting at previous offset
 echo '';                           #   ending at default (fdisk should propose max)
 echo 'p';                          # print
 echo 'w') | fdisk iotbox.img       # write and quit

LOOP=$(kpartx -avs iotbox.img)
LOOP_MAPPER_PATH=$(echo "${LOOP}" | tail -n 1 | awk '{print $3}')
LOOP_PATH="/dev/${LOOP_MAPPER_PATH::-2}"
LOOP_MAPPER_PATH="/dev/mapper/${LOOP_MAPPER_PATH}"
LOOP_MAPPER_BOOT=$(echo "${LOOP}" | tail -n 2 | awk 'NR==1 {print $3}')
LOOP_MAPPER_BOOT="/dev/mapper/${LOOP_MAPPER_BOOT}"

sleep 5

# resize filesystem
e2fsck -f "${LOOP_MAPPER_PATH}" # resize2fs requires clean fs
resize2fs "${LOOP_MAPPER_PATH}"

mkdir -p "${MOUNT_POINT}" #-p: no error if existing
mount "${LOOP_MAPPER_PATH}" "${MOUNT_POINT}"
mount "${LOOP_MAPPER_BOOT}" "${MOUNT_POINT}/boot/"

QEMU_ARM_STATIC="/usr/bin/qemu-arm-static"
cp "${QEMU_ARM_STATIC}" "${MOUNT_POINT}/usr/bin/"

# 'overlay' the overwrite directory onto the mounted image filesystem
cp -a "${OVERWRITE_FILES_BEFORE_INIT_DIR}"/* "${MOUNT_POINT}"
chroot "${MOUNT_POINT}" /bin/bash -c "sudo /etc/init_posbox_image.sh"

# get rid of the git clone
rm -rf "${CLONE_DIR}"
# and the ngrok usr/bin
rm -rf "${OVERWRITE_FILES_BEFORE_INIT_DIR}/usr"
cp -av "${OVERWRITE_FILES_AFTER_INIT_DIR}"/* "${MOUNT_POINT}"

find "${MOUNT_POINT}"/ -type f -name "*.iotpatch"|while read iotpatch; do
    DIR=$(dirname "${iotpatch}")
    BASE=$(basename "${iotpatch%.iotpatch}")
    find "${DIR}" -type f -name "${BASE}" ! -name "*.iotpatch"|while read file; do
        patch -f "${file}" < "${iotpatch}"
    done
done

# cleanup
umount -f "${MOUNT_POINT}"/boot/
umount -f "${MOUNT_POINT}"
rm -rf "${MOUNT_POINT}"

echo "Running zerofree..."
zerofree -v "${LOOP_MAPPER_PATH}" || true

kpartx -d "${LOOP_PATH}"
