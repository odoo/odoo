# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.http.router

from odoo.addons.iot_drivers.tools.system import IS_TEST

if not IS_TEST:
    # Test IoT system is expected to handle Odoo database unlike "real" IoT systems.

    def db_list(force=False, host=None):
        return []

    odoo.http.router.db_list = db_list
