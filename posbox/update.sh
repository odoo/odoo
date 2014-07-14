#!/bin/bash -x
git pull origin posbox;
/home/pi/odoo/openerp-server -u base --stop-after-init;
