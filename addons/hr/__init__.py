# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard
from . import report


def uninstall_hook(env):
    # put the rules back to their original domain (TRUE)
    if rule := env.ref('base.res_partner_bank_rule_user', raise_if_not_found=False):
        rule.active = True
    if rule := env.ref('base.res_partner_bank_rule_user_1', raise_if_not_found=False):
        rule.active = True
