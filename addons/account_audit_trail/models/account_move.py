# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import logging

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.ondelete(at_uninstall=False)
    def _unlink_account_audit_trail_except_once_post(self):
        if not self._context.get('force_delete') and any(
            move.posted_before and move.company_id.check_account_audit_trail
            for move in self
        ):
            raise UserError(_("To keep the audit trail, you can not delete journal entries once they have been posted.\nInstead, you can cancel the journal entry."))

    def unlink(self):
        # Add logger here because in api ondelete account.move.line is deleted and we can't get total amount
        logger_msg = False
        if any(m.posted_before and m.company_id.check_account_audit_trail for m in self):
            if self._context.get('force_delete'):
                moves_details = []
                for move in self:
                    entry_details = "{move_name} ({move_id}) amount {amount_total} {currency} and partner {partner_name}".format(
                        move_name=move.name,
                        move_id=move.id,
                        amount_total=move.amount_total,
                        currency=move.currency_id.name,
                        partner_name=move.partner_id.display_name,
                    )
                    account_balances_per_account = defaultdict(float)
                    for line in move.line_ids:
                        account_balances_per_account[line.account_id] += line.balance
                    account_details = "\n".join(
                        "- {account_name} ({account_id}) with balance {balance} {currency}".format(
                            account_name=account.name,
                            account_id=account.id,
                            balance=balance,
                            currency=line.currency_id.name,
                        )
                        for account, balance in account_balances_per_account.items()
                    )
                    moves_details.append("{entry_details}\n{account_details}".format(
                        entry_details=entry_details, account_details=account_details
                    ))
                logger_msg = "\nForce deleted Journal Entries by {user_name} ({user_id})\nEntries\n{moves_details}".format(
                    user_name=self.env.user.name,
                    user_id=self.env.user.id,
                    moves_details="\n".join(moves_details),
                )
        res = super().unlink()
        if logger_msg:
            _logger.info(logger_msg)
        return res
