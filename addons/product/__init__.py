# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import populate
from . import wizard

def _post_init_hook(env):
    companies = env['res.company'].search([])
    country_codes = ['US', 'MM', 'LR']

    if all(c.country_id.code in country_codes for c in companies):
        env['ir.config_parameter'].sudo().set_param('product.weight_in_lbs', '1')
        env['ir.config_parameter'].sudo().set_param('product.volume_in_cubic_feet', '1')
