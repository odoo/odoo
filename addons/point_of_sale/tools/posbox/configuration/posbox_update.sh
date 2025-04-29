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

sudo service led-status start
