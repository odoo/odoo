#!/bin/bash

# set openerp-server.conf
echo "[options]
; This is the password that allows database operations:
; admin_passwd = admin
db_host = $DB_PORT_5432_TCP_ADDR
db_port = $DB_PORT_5432_TCP_PORT
db_user = odoo
db_password = odoo
addons_path = /usr/lib/python2.7/dist-packages/openerp/addons" > /etc/odoo/openerp-server.conf

# create log file to prevent tail from displaying warnings
touch /var/log/odoo/odoo-server.log
chmod o+rw /var/log/odoo/odoo-server.log

# start odoo
su odoo -s /bin/bash -c "/usr/bin/openerp-server --config /etc/odoo/openerp-server.conf --addons-path /usr/lib/python2.7/dist-packages/openerp/addons"

# display logs
tail -F /var/log/odoo/odoo-server.log
