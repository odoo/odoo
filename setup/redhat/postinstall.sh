#!/bin/sh

set -e

ODOO_CONFIGURATION_DIR=/etc/odoo
ODOO_CONFIGURATION_FILE=$ODOO_CONFIGURATION_DIR/openerp-server.conf
ODOO_DATA_DIR=/var/lib/odoo
ODOO_GROUP="odoo"
ODOO_LOG_DIR=/var/log/odoo
ODOO_USER="odoo"

if ! getent passwd | grep -q "^odoo:"; then
    groupadd $ODOO_GROUP
    adduser --system --no-create-home $ODOO_USER -g $ODOO_GROUP
fi
# Register "$ODOO_USER" as a postgres superuser
su - postgres -c "createuser -s $ODOO_USER" 2> /dev/null || true
# Configuration file
mkdir -p $ODOO_CONFIGURATION_DIR
# can't copy debian config-file as addons_path is not the same
echo "[options]
; This is the password that allows database operations:
; admin_passwd = admin
db_host = False
db_port = False
db_user = $ODOO_USER
db_password = False
addons_path = /usr/lib/python2.7/site-packages/openerp/addons
" > $ODOO_CONFIGURATION_FILE
chown $ODOO_USER:$ODOO_GROUP $ODOO_CONFIGURATION_FILE
chmod 0640 $ODOO_CONFIGURATION_FILE
# Log
mkdir -p $ODOO_LOG_DIR
chown $ODOO_USER:$ODOO_GROUP $ODOO_LOG_DIR
chmod 0750 $ODOO_LOG_DIR
# Data dir
mkdir -p $ODOO_DATA_DIR
chown $ODOO_USER:$ODOO_GROUP $ODOO_DATA_DIR

INIT_FILE=/lib/systemd/system/odoo.service
touch $INIT_FILE
chmod 0700 $INIT_FILE
cat << 'EOF' > $INIT_FILE
[Unit]
Description=Odoo Open Source ERP and CRM
After=network.target

[Service]
Type=simple
User=odoo
Group=odoo
ExecStart=/usr/bin/odoo.py --config=/etc/odoo/openerp-server.conf

[Install]
WantedBy=multi-user.target
EOF
easy_install pyPdf vatnumber pydot psycogreen
