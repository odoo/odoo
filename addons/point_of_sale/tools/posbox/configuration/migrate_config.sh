#!/usr/bin/env bash

ODOO_CONF=$(</home/pi/odoo.conf)

migrate_setting() {
    TARGET_FILE="$1"
    CONF_KEY="$2"
    APPEND="$3"
    if [ ! -f "$TARGET_FILE" ] || [ -n "$APPEND" ]
    then
        REGEX="$CONF_KEY = ([^[:space:]]+)"
        if [[ "$ODOO_CONF" =~ $REGEX ]]
        then
            VALUE=${BASH_REMATCH[1]}
            echo "$VALUE" >> "$TARGET_FILE"
            SETTINGS_MIGRATED='true'
        fi
    fi
}

migrate_setting '/home/pi/odoo-remote-server.conf'    'remote_server'
migrate_setting '/home/pi/token'                      'token'
migrate_setting '/home/pi/odoo-db-uuid.conf'          'db_uuid'
migrate_setting '/home/pi/odoo-enterprise-code.conf'  'enterprise_code'
migrate_setting '/home/pi/odoo-subject.conf'          'subject'

if [ ! -f '/home/pi/wifi_network.txt' ]
then
    migrate_setting '/home/pi/wifi_network.txt'       'wifi_ssid'
    migrate_setting '/home/pi/wifi_network.txt'       'wifi_password'   'true'
fi

if [ -n "$SETTINGS_MIGRATED" ]
then
    cp '/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/odoo.conf' '/home/pi/odoo.conf'
fi
