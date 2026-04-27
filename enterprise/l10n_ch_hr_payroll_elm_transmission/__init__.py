# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

"""
tbd
def _post_init_hook(env):
    env['res.company'].search([]).filtered(lambda c: c.country_id.code == 'CH')._initialize_insurances()
"""