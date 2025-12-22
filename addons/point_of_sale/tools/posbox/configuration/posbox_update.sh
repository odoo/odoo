#!/usr/bin/env bash

sudo service led-status stop

cd /home/pi/odoo
localbranch=$(git symbolic-ref -q --short HEAD)
localremote=$(git config branch.$localbranch.remote)

if [[ "$(git remote get-url "$localremote")" != *odoo/odoo* ]]; then
    git remote set-url "${localremote}" "https://github.com/odoo/odoo.git"
fi

echo "addons/point_of_sale/tools/posbox/overwrite_after_init/home/pi/odoo" >> .git/info/sparse-checkout
echo "addons/iot_base" >> .git/info/sparse-checkout
echo "addons/iot_drivers" >> .git/info/sparse-checkout
echo "addons/iot_box_image/configuration" >> .git/info/sparse-checkout
echo "setup/iot_box_builder/configuration" >> .git/info/sparse-checkout

git fetch "${localremote}" "${localbranch}" --depth=1
git reset "${localremote}"/"${localbranch}" --hard

sudo git clean -dfx
if [ -d /home/pi/odoo/addons/point_of_sale/tools/posbox/overwrite_after_init ]; then
    cp -a /home/pi/odoo/addons/point_of_sale/tools/posbox/overwrite_after_init/home/pi/odoo/* /home/pi/odoo/
    rm -r /home/pi/odoo/addons/point_of_sale/tools/posbox/overwrite_after_init
fi

# TODO: Remove this code when v16 is deprecated
odoo_conf="addons/point_of_sale/tools/posbox/configuration/odoo.conf"
if ! grep -q "server_wide_modules" $odoo_conf; then
    echo "server_wide_modules=hw_drivers,hw_escpos,hw_posbox_homepage,point_of_sale,web" >> $odoo_conf
fi

if [ -d /home/pi/odoo/addons/iot_drivers ]; then
  # TODO: remove this when v18.0 is deprecated (hw_drivers/,hw_posbox_homepage/ -> iot_drivers/)
  sed -i 's|hw_drivers.*hw_posbox_homepage|iot_drivers|g' /home/pi/odoo.conf
fi

# we create a symlinks in case the image uses hardcoded paths (ramdisks.service for example)
if [ -d /home/pi/odoo/addons/iot_box_image ]; then
  # if we have the iot_box_image module, it means configuration files are not in point_of_sale anymore
  mkdir -p /home/pi/odoo/addons/point_of_sale/tools/posbox
  ln -sf /home/pi/odoo/addons/iot_box_image/configuration /home/pi/odoo/addons/point_of_sale/tools/posbox
fi

if [ -d /home/pi/odoo/setup/iot_box_builder ]; then
  # if we have the iot_box_builder module, it means configuration files are not in point_of_sale anymore
  # in case ramdisks.service points to point_of_sale, we create a symlink
  mkdir -p /home/pi/odoo/addons/point_of_sale/tools/posbox
  ln -sf /home/pi/odoo/setup/iot_box_builder/configuration /home/pi/odoo/addons/point_of_sale/tools/posbox
  # in case ramdisks.service points to iot_box_image, we create a symlink
  mkdir -p /home/pi/odoo/addons/iot_box_image
  ln -sf /home/pi/odoo/setup/iot_box_builder/configuration /home/pi/odoo/addons/iot_box_image
fi

sudo service led-status start
