#!/usr/bin/env bash

cp -a /home/pi/odoo/addons/point_of_sale/tools/posbox/overwrite_after_init/home/pi/odoo/* /home/pi/odoo/
rm -r /home/pi/odoo/addons/point_of_sale/tools/posbox/overwrite_after_init

sudo find / -type f -name "*.iotpatch" 2> /dev/null | while read iotpatch; do
    DIR=$(dirname "${iotpatch}")
    BASE=$(basename "${iotpatch%.iotpatch}")
    sudo find "${DIR}" -type f -name "${BASE}" ! -name "*.iotpatch" | while read file; do
        sudo patch -f "${file}" < "${iotpatch}"
    done
done
