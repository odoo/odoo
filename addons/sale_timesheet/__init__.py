# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import controllers
from . import models
from . import wizard
from . import report


def uninstall_hook(env):
    if rule := env.ref("account.account_analytic_line_rule_billing_user", raise_if_not_found=False):
        rule.active = True
    if rule := env.ref("account.account_analytic_line_rule_readonly_user", raise_if_not_found=False):
        rule.active = True


def _sale_timesheet_post_init(env):
    products = env['product.template'].search([
        ('type', '=', 'service'),
        ('service_tracking', 'in', ['no', 'task_global_project', 'task_in_project', 'project_only']),
        ('invoice_policy', '=', 'order'),
        ('service_type', '=', 'manual'),
    ])

    for product in products:
        product.service_type = 'timesheet'
        product._compute_service_policy()

    lines = env['account.analytic.line'].search(['&', '|',
        ('billable_type', '=', '30_other_costs'),
        ('billable_type', '=', '11_other_revenues'),
        ('project_id', '!=', False),
    ])
    lines._compute_project_billable_type()
