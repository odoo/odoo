# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID

from . import controllers
from . import models
from . import wizard
from . import report


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    module_domain = "('project_id', '=', False)"
    original_domain = "(1, '=', 1)"
    rule = env.ref('account.account_analytic_line_rule_billing_user', raise_if_not_found=False)
    if rule and rule.domain_force:
        rule.domain_force = rule.domain_force.replace(module_domain, original_domain)
