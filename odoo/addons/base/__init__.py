# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import populate
from . import report
from . import wizard
from odoo import tools


def post_init(cr, registry):
    """Rewrite ICP's to force groups
    Load states only once"""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.config_parameter'].init(force=True)

    tools.convert.convert_file(cr, 'base', 'data/res.country.state.csv', noupdate=True)
