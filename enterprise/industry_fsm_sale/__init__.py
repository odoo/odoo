# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard


def post_init(env):
    env['project.project'].search([('is_fsm', '=', True)]).write({
        'allow_billable': True,
        'allow_material': True,
        'allow_timesheets': True,
        'timesheet_product_id': env.ref('sale_timesheet.time_product')
    })


def uninstall_hook(env):
    """ TODO: remove me in master """
    pass
