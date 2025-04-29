#!/usr/bin/env bash

sudo mount -o remount,rw /

sudo service odoo stop

cd /home/pi/odoo
localbranch=$(git symbolic-ref -q --short HEAD)
localremote=$(git config branch.$localbranch.remote)

echo "addons/point_of_sale/tools/posbox/overwrite_after_init/home/pi/odoo" >> .git/info/sparse-checkout
echo "addons/iot_base" >> .git/info/sparse-checkout

git fetch "${localremote}" "${localbranch}" --depth=1
git reset "${localremote}"/"${localbranch}" --hard

git clean -dfx
cp -a /home/pi/odoo/addons/point_of_sale/tools/posbox/overwrite_after_init/home/pi/odoo/* /home/pi/odoo/
rm -r /home/pi/odoo/addons/point_of_sale/tools/posbox/overwrite_after_init

sudo mount -o remount,ro /
sudo mount -o remount,rw /root_bypass_ramdisks/etc/cups

(sleep 5 && sudo service odoo restart) &
