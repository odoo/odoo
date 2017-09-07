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
require_command qemu-system-arm
require_command zerofree

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
__file="${__dir}/$(basename "${BASH_SOURCE[0]}")"
__base="$(basename ${__file} .sh)"

MOUNT_POINT="${__dir}/root_mount"
OVERWRITE_FILES_BEFORE_INIT_DIR="${__dir}/overwrite_before_init"
OVERWRITE_FILES_AFTER_INIT_DIR="${__dir}/overwrite_after_init"

if [ ! -f kernel-qemu ] || ! file_exists *raspbian*.img ; then
    ./posbox_download_images.sh
fi

cp -a *raspbian*.img posbox.img

CLONE_DIR="${OVERWRITE_FILES_BEFORE_INIT_DIR}/home/pi/odoo"

rm -rf "${CLONE_DIR}"

if [ ! -d $CLONE_DIR ]; then
    echo "Clone Github repo"
    mkdir -p "${CLONE_DIR}"
    git clone -b 8.0 --no-local --no-checkout --depth 1 https://github.com/odoo/odoo.git "${CLONE_DIR}"
    cd "${CLONE_DIR}"
    git config core.sparsecheckout true
    echo "addons/web
addons/web_kanban
addons/hw_*
addons/point_of_sale/tools/posbox/configuration
openerp/
odoo.py" | tee --append .git/info/sparse-checkout > /dev/null
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
dd if=/dev/zero bs=1M count=2048 >> posbox.img

# resize partition table
echo "Fdisking"
START_OF_ROOT_PARTITION=$(fdisk -l posbox.img | tail -n 1 | awk '{print $2}')
(echo 'p';                          # print
 echo 'd';                          # delete
 echo '2';                          #   second partition
 echo 'n';                          # create new partition
 echo 'p';                          #   primary
 echo '2';                          #   number 2
 echo "${START_OF_ROOT_PARTITION}"; #   starting at previous offset
 echo '';                           #   ending at default (fdisk should propose max)
 echo 'p';                          # print
 echo 'w') | fdisk posbox.img       # write and quit

LOOP_MAPPER_PATH=$(kpartx -avs posbox.img | tail -n 1 | cut -d ' ' -f 3)
LOOP_MAPPER_PATH="/dev/mapper/${LOOP_MAPPER_PATH}"
sleep 5

# resize filesystem
e2fsck -f "${LOOP_MAPPER_PATH}" # resize2fs requires clean fs
resize2fs "${LOOP_MAPPER_PATH}"

mkdir "${MOUNT_POINT}"
mount "${LOOP_MAPPER_PATH}" "${MOUNT_POINT}"

# 'overlay' the overwrite directory onto the mounted image filesystem
cp -a "${OVERWRITE_FILES_BEFORE_INIT_DIR}"/* "${MOUNT_POINT}"

# get rid of the git clone
rm -rf "${CLONE_DIR}"
# and the ngrok usr/bin
rm -rf "${OVERWRITE_FILES_BEFORE_INIT_DIR}/usr"

# get rid of the mount, we have to remount it anyway because we have
# to "refresh" the filesystem after qemu modified it
sleep 2
umount "${MOUNT_POINT}"

# from http://paulscott.co.za/blog/full-raspberry-pi-raspbian-emulation-with-qemu/
# ssh pi@localhost -p10022
QEMU_OPTS=(-kernel kernel-qemu -cpu arm1176 -m 256 -M versatilepb -no-reboot -serial stdio -append 'root=/dev/sda2 rootfstype=ext4 rw' -hda posbox.img -net user,hostfwd=tcp::10022-:22,hostfwd=tcp::18069-:8069 -net nic)
if [ -z ${DISPLAY:-} ] ; then
    QEMU_OPTS+=(-nographic)
fi
qemu-system-arm "${QEMU_OPTS[@]}"

mount "${LOOP_MAPPER_PATH}" "${MOUNT_POINT}"
cp -av "${OVERWRITE_FILES_AFTER_INIT_DIR}"/* "${MOUNT_POINT}"

# cleanup
sleep 2
umount "${MOUNT_POINT}"
rm -r "${MOUNT_POINT}"

echo "Running zerofree..."
zerofree -v "${LOOP_MAPPER_PATH}" || true

kpartx -d posbox.img
