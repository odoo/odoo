#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

set -x  # display commands before execution

# Full upgrade
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew"

# add Tailscale apt repository
curl -fsSL https://pkgs.tailscale.com/stable/raspbian/bullseye.noarmor.gpg | tee /usr/share/keyrings/tailscale-archive-keyring.gpg > /dev/null
curl -fsSL https://pkgs.tailscale.com/stable/raspbian/bullseye.tailscale-keyring.list | tee /etc/apt/sources.list.d/tailscale.list

# Switch to Trixie packages
sed -i 's|bookworm|trixie|g' /etc/apt/sources.list
sed -i 's|bookworm|trixie|g' /etc/apt/sources.list.d/raspi.list
apt-get update
apt-get autoremove -y

# Upgrade all packages to Trixie versions
DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" --purge --auto-remove

# Reinstall packages needed in saas-19.1
apt-get install -y chromium python3-lxml-html-clean apt-transport-https tailscale

# Disable read-only on boot
sed -i 's|,ro|   |g' /etc/fstab

# Fix sparse-checkout
echo setup/iot_box_builder/configuration | tee -a /home/pi/odoo/.git/info/sparse-checkout
echo setup/iot_box_builder/overwrite_after_init/etc | tee -a /home/pi/odoo/.git/info/sparse-checkout

# Fix services
sed -i 's|After=.*|After=network-online.target time-sync.target cups.socket NetworkManager.service rc-local.service|g' /etc/systemd/system/odoo.service
sed -i 's|Wants=.*|Wants=network-online.target time-sync.target|g' /etc/systemd/system/odoo.service
sed -i '/Environment="LIBCAMERA_LOG_LEVELS=3"/a Environment="ODOO_PY_COLORS=True"' /etc/systemd/system/odoo.service
sed -i 's|ExecStart=.*|ExecStart=/etc/setup_ramdisks.sh|g' /etc/systemd/system/ramdisks.service
sed -i 's|ExecStart=.*|ExecStart=/etc/led_manager.sh|g' /etc/systemd/system/odoo-led-manager.service

# Fix LNA popup in Chromium
mkdir -p /etc/chromium/policies/managed
echo '{"LocalNetworkAccessAllowedForUrls":["*"]}' | tee /etc/chromium/policies/managed/local_access.json
