#!/bin/bash -x
/home/pi/odoo/openerp-server --db-filter=posbox -d posbox --log-level=debug --load=web,hw_posbox_homepage,hw_posbox_upgrade

