# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from . import models
from . import wizards
from . import demo


def _post_init_hook(env):
    env['account.chart.template']._load_pre_defined_data({
        'res.company': {'withholding_tax_base_account_id'},
    })
