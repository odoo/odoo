#!/usr/bin/env bash

cd /home/pi/odoo
localbranch=$(git symbolic-ref -q --short HEAD)
localremote=$(git config branch.$localbranch.remote)

if [[ "$(git remote get-url "$localremote")" != *odoo/odoo* ]]; then
    git remote set-url "${localremote}" "https://github.com/odoo/odoo.git"
fi

echo "addons/iot_base" >> .git/info/sparse-checkout
echo "addons/iot_drivers" >> .git/info/sparse-checkout

git fetch "${localremote}" "${localbranch}" --depth=1
git reset "${localremote}"/"${localbranch}" --hard
sudo git clean -dfx

if [ -d /home/pi/odoo/addons/point_of_sale ]; then
  # TODO: remove this when v18.0 is deprecated (point_of_sale/tools/posbox/ -> iot_box_image/)
  sudo sed -i 's|iot_box_image|point_of_sale/tools/posbox|g' /root_bypass_ramdisks/etc/systemd/system/ramdisks.service

  # TODO: Remove this code when v16 is deprecated
  odoo_conf="addons/point_of_sale/tools/posbox/configuration/odoo.conf"
  if ! grep -q "server_wide_modules" $odoo_conf; then
      echo "server_wide_modules=hw_drivers,hw_posbox_homepage,web" >> $odoo_conf
  fi
fi

if [ -d /home/pi/odoo/addons/iot_drivers ]; then
  # TODO: remove this when v18.0 is deprecated (hw_drivers/,hw_posbox_homepage/ -> iot_drivers/)
  sed -i 's|hw_drivers.*hw_posbox_homepage|iot_drivers|g' /home/pi/odoo.conf
fi
