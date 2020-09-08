#!/usr/bin/env bash

PATH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sudo mount -o remount,rw /

sudo service led-status stop

cd /home/pi/odoo
localbranch=$(git symbolic-ref -q --short HEAD)
localremote=$(git config branch.$localbranch.remote)

echo "addons/point_of_sale/tools/posbox/overwrite_after_init/home/pi/odoo" >> .git/info/sparse-checkout

git fetch "${localremote}" "${localbranch}" --depth=1
git reset "${localremote}"/"${localbranch}" --hard

git clean -df

sudo ${PATH_DIR}/post_reset_hook.sh

sudo mount -o remount,ro /
sudo mount -o remount,rw /root_bypass_ramdisks/etc/cups

sudo service led-status start

(sleep 5 && sudo service odoo restart) &
