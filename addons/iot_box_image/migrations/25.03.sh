if [ -d /home/pi/odoo/addons/point_of_sale ]; then
    # Added in v18.0 (point_of_sale/tools/posbox/ -> iot_box_image/)
    sed -i 's|iot_box_image|point_of_sale/tools/posbox|g' /root_bypass_ramdisks/etc/systemd/system/ramdisks.service

    # Necessary for images based on v16.0 as they used the old service (not systemd)
    odoo_conf="addons/point_of_sale/tools/posbox/configuration/odoo.conf"
    if ! grep -q "server_wide_modules" $odoo_conf; then
        echo "server_wide_modules=hw_drivers,hw_posbox_homepage,web" >> $odoo_conf
    fi
fi

usermod -aG input odoo
