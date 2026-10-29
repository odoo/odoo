# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from . import models
from . import wizard

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """ The expenses paid before this module was installed have no journal entry to follow: keep them paid. """
    Expense = env['hr.expense']
    Expense.flush_model(['state', 'account_move_id', 'marked_as_paid'])
    # In SQL as `write` refuses to mark an expense as paid without a journal entry
    env.cr.execute("""
        UPDATE hr_expense
           SET marked_as_paid = TRUE
         WHERE state = 'paid'
           AND account_move_id IS NULL
           AND marked_as_paid IS NOT TRUE
    """)
    if env.cr.rowcount:
        _logger.info("%s expenses paid without journal entry are kept as paid", env.cr.rowcount)
    Expense.invalidate_model(['marked_as_paid'])


def uninstall_hook(env):
    """Re-enable the employee rule of `hr_expense` disabled by this module."""
    access_rule = env.ref('hr_expense.ir_rule_hr_expense_employee', raise_if_not_found=False)
    if access_rule:
        access_rule.active = True
