#!/bin/bash -x
/home/pi/odoo/openerp-server --db-filter=posbox -d posbox --log-level=info --load=web,hw_posbox_homepage,hw_posbox_upgrade

