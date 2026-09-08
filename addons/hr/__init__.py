# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard
from . import report


def uninstall_hook(env):
    # put the rule back to its original domain (TRUE)
    if rule := env.ref('base.res_partner_bank_rule_user_1', raise_if_not_found=False):
        rule.active = True
