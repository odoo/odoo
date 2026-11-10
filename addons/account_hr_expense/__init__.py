# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def uninstall_hook(env):
    """Re-enable the employee rule of `hr_expense` disabled by this module."""
    access_rule = env.ref('hr_expense.ir_rule_hr_expense_employee', raise_if_not_found=False)
    if access_rule:
        access_rule.active = True
