#!/usr/bin/env bash

cd /home/pi/odoo
localbranch=$(git symbolic-ref -q --short HEAD)
localremote=$(git config branch.$localbranch.remote)

if [[ "$(git remote get-url "$localremote")" != *odoo/odoo* ]]; then
  git remote set-url "${localremote}" "https://github.com/odoo/odoo.git"
fi

echo "addons/iot_base" >> .git/info/sparse-checkout
echo "addons/iot_drivers" >> .git/info/sparse-checkout
# compatibility with v19.1+
echo "setup/iot_box_builder" >> .git/info/sparse-checkout

git fetch "${localremote}" "${localbranch}" --depth=1
git reset "${localremote}"/"${localbranch}" --hard
sudo git clean -dfx

# Update requirements
REQUIREMENTS_FILE="/home/pi/odoo/addons/iot_box_image/configuration/requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
  pip3 install --upgrade -r "$REQUIREMENTS_FILE" --user --break-system-package
fi

PACKAGES_FILE="/home/pi/odoo/addons/iot_box_image/configuration/packages.txt"
if [ -f "$PACKAGES_FILE" ]; then
  # Update packages: install new ones, upgrade existing ones in the background
  sudo chroot /root_bypass_ramdisks/ /bin/bash <<@EOF
    mount -t proc proc /proc
    apt-get update
    xargs apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install < "$PACKAGES_FILE"
    nohup bash -c "apt-get upgrade -y && apt-get -y autoremove" > /dev/null 2>&1 &  # Run in background to avoid blocking the script
@EOF
fi

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
  sudo sed -i 's|hw_drivers.*hw_posbox_homepage|iot_drivers|g' /home/pi/odoo.conf
  # ensure ownership remains correct
  sudo chown odoo:odoo /home/pi/odoo.conf
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
