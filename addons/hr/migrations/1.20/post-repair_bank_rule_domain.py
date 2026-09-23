"""Rewrite the bank-account record rule that a `noupdate` kept on a dead field.

`ir_rule_res_partner_bank_internal_users` is declared under `noupdate="1"`, so
no upgrade rewrites it once it exists. `res.partner.bank.partner_ids` is
`partner_id` again, and the 1.18 script that carried this rule the other way
left the stored row naming the many2many:

    ValueError: Invalid field res.partner.bank.partner_ids
                in condition ('partner_ids.employee_ids', '=', False)

It surfaces only where the rule is evaluated -- an invoice form, a partner's
bank tab -- which is why the same defect read as an intermittent fault the last
time this field changed shape rather than as a broken rule. Repairing the row is
the whole fix; the rule's meaning is unchanged.

`marin190` was repaired as data the day the holder was restored, so this script
exists for the copies and restores that were taken before that, and it is
guarded so a database already holding the right domain is left alone.
"""

import logging

from odoo.addons.base.models.ir_access_convert import rewrite_converted_domain

_logger = logging.getLogger(__name__)

MODULE = "hr"
NAME = "ir_rule_res_partner_bank_internal_users"
CORRECT = "[('partner_id.employee_ids', '=', False)]"


def migrate(cr, version):
    """Point the rule back at the single holder.

    :param cr: database cursor
    :param version: installed module version; falsy on a fresh install
    """
    if not version:
        return
    rewrite_converted_domain(cr, MODULE, NAME, CORRECT, logger=_logger)
