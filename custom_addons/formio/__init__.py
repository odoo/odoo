# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

from . import models
from . import controllers
from . import utils
from . import wizard

import odoo
from odoo import api, SUPERUSER_ID
from functools import partial


def uninstall_hook(cr, registry):
    def delete_config_parameter(dbname):
        db_registry = odoo.modules.registry.Registry.new(dbname)
        with api.Environment.manage(), db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['ir.config_parameter'].search(
                [('key', '=', 'formio.default_builder_js_options_id')]).unlink()
    cr.postcommit.add(partial(delete_config_parameter, cr.dbname))
