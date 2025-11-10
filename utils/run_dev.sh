#!/bin/bash

DB_NAME="odoo"
CONFIG_FILE="utils/config/odoo.conf"

cd ..
./odoo-bin --addons-path="addons/,../tutorials" \
    --config=${CONFIG_FILE}                     \
    -d ${DB_NAME}
