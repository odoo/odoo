# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.api import Environment, SUPERUSER_ID
import logging


def update_tax_calculation_rounding_method(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    env['res.company'].search(
        [('partner_id.country_id', '=', env.ref('base.cl').id)]).write({
            'tax_calculation_rounding_method': 'round_globally', })


def post_init_hook(cr, registry):
    """Loaded after installing the module.
    This module's DB modifications will be available.
    :param odoo.sql_db.Cursor cr:
        Database cursor.
    :param odoo.modules.registry.Registry registry:
        Database registry, using v7 api.
    """
    update_tax_calculation_rounding_method(cr, registry)
