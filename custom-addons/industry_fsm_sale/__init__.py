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
    """ When sale_timesheet is uninstalled, the product 'sale_timesheet.time_product' is deleted.
        Yet, this module adds a constraint on project that checks
        that the timesheet_product_id is not null if allow_billable.
        This method unsets allow_billable on projects with this product to allow its deletion. """
    env['project.project'].with_context(active_test=False).search(
        [('allow_billable', '=', True), ('timesheet_product_id', '=', env.ref('sale_timesheet.time_product').id)]
    ).allow_billable = False
