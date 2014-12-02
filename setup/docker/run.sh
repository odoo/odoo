#!/bin/bash

service postgresql start 

# create log file to prevent tail from displaying warnings
touch /var/log/odoo/odoo-server.log
chmod o+rw /var/log/odoo/odoo-server.log

service odoo start

tail -F /var/log/odoo/odoo-server.log