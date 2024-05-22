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
