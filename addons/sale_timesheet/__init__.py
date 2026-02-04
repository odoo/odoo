# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import controllers
from . import models
from . import wizard
from . import report


def uninstall_hook(env):
    env.ref("account.account_analytic_line_rule_billing_user").write({'domain_force': "[(1, '=', 1)]"})
    rule_readonly_user = env.ref("account.account_analytic_line_rule_readonly_user", raise_if_not_found=False)
    if rule_readonly_user:
        rule_readonly_user.write({'domain_force': "[(1, '=', 1)]"})

def _sale_timesheet_post_init(env):
    products = env['product.template'].search([('detailed_type', '=', 'service'), ('invoice_policy', '=', 'order'), ('service_type', '=', 'manual')])

    for product in products:
        product.service_type = 'timesheet'
        product._compute_service_policy()
