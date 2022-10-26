# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import controllers
from . import models
from . import wizard
from . import report

from odoo import api, SUPERUSER_ID

def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    env.ref("account.account_analytic_line_rule_billing_user").write({'domain_force': "[(1, '=', 1)]"})

def _sale_timesheet_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    products = env['product.template'].search([('detailed_type', '=', 'service'), ('invoice_policy', '=', 'order'), ('service_type', '=', 'manual')])

    for product in products:
        product.service_type = 'timesheet'
        product._compute_service_policy()
