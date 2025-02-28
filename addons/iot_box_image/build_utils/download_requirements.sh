#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

require_command git
require_command tar
require_command unxz
require_command unzip
require_command wget

__dir=$1

# Ask user for branch/version and repository info
current_branch="$(git branch --show-current)"
read -p "Enter dev branch [${current_branch}]: " VERSION
VERSION=${VERSION:-$current_branch}

current_remote=$(git config branch.$current_branch.remote)
current_repo="$(git remote get-url $current_remote | sed 's/.*github.com[\/:]//' | sed 's/\/odoo.git//')"
read -p "Enter repo [${current_repo}]: " REPO
REPO="https://github.com/${REPO:-$current_repo}/odoo.git"
echo "Using repo: ${REPO}"

CLONE_DIR="${OVERWRITE_FILES_BEFORE_INIT_DIR}/home/pi/odoo"
if [ ! -d "$CLONE_DIR" ]; then
    echo "Clone GitHub repo"
    mkdir -pv "${CLONE_DIR}"
    git clone -b ${VERSION} --no-local --no-checkout --depth=1 ${REPO} "${CLONE_DIR}"
    cd "${CLONE_DIR}"
    git config core.sparsecheckout true
    tee -a .git/info/sparse-checkout < "${BUILD_UTILS_DIR}/sparse-checkout" > /dev/null
    git read-tree -mu HEAD
    git remote set-url origin "https://github.com/odoo/odoo.git" # ensure remote is the original repo
fi
cd "${__dir}"

# Download and extract the Raspberry Pi OS image if not present.
if ! file_exists *raspios*.img ; then
    wget "https://downloads.raspberrypi.com/raspios_lite_armhf/images/raspios_lite_armhf-2024-11-19/2024-11-19-raspios-bookworm-armhf-lite.img.xz" -O raspios.img.xz
    unxz --verbose raspios.img.xz
fi
RASPIOS=$(echo *raspios*.img)

# Download ngrok for ARM and place it in the overwrite directory.
USR_BIN="${OVERWRITE_FILES_BEFORE_INIT_DIR}/usr/bin/"
mkdir -pv "${USR_BIN}"
if ! file_exists "${USR_BIN}/ngrok" ; then
    wget -O /tmp/ngrok.tgz 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm.tgz'
    tar xvzf /tmp/ngrok.tgz -C "${USR_BIN}" --remove-files
fi
