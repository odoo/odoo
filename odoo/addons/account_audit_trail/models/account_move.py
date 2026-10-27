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
        if not self.env.context.get('force_delete') and self._is_protected_by_audit_trail():
            raise UserError(_("To keep the audit trail, you can not delete journal entries once they have been posted.\nInstead, you can cancel the journal entry."))

    def unlink(self):
        if self.env.context.get('soft_delete'):
            self.button_cancel()
            return True
        # Add logger here because in api ondelete account.move.line is deleted and we can't get total amount
        logger_msg = False
        if self.env.context.get('force_delete') and self._is_protected_by_audit_trail():
            moves_details = []
            for move in self:
                entry_details = f"{move.name} ({move.id}) amount {move.amount_total} {move.currency_id.name} and partner {move.partner_id.display_name}"
                account_balances_per_account = defaultdict(float)
                for line in move.line_ids:
                    account_balances_per_account[line.account_id] += line.balance
                account_details = "\n".join(
                    f"- {account.name} ({account.id}) with balance {balance} {move.currency_id.name}"
                    for account, balance in account_balances_per_account.items()
                )
                moves_details.append(f"{entry_details}\n{account_details}")
            moves_details = "\n".join(moves_details)
            logger_msg = f"\nForce deleted Journal Entries by {self.env.user.name} ({self.env.user.id})\nEntries\n{moves_details}"
        res = super().unlink()
        if logger_msg:
            _logger.info(logger_msg)
        return res

    def _is_protected_by_audit_trail(self):
        return any(move.posted_before and move.company_id.check_account_audit_trail for move in self)
