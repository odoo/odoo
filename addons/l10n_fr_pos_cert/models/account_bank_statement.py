# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    @api.ondelete(at_uninstall=True)
    def _unlink_except_created_by_pos(self):
        for statement in self.filtered(lambda s: s.company_id._is_accounting_unalterable() and s.journal_id.pos_payment_method_ids):
            raise UserError(_('You cannot modify anything on a bank statement (name: %s) that was created by point of sale operations.') % (statement.name,))


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    @api.ondelete(at_uninstall=True)
    def _unlink_except_created_by_pos(self):
        for line in self.filtered(lambda s: s.company_id._is_accounting_unalterable() and s.journal_id.pos_payment_method_ids):
            raise UserError(_('You cannot modify anything on a bank statement line (name: %s) that was created by point of sale operations.') % (line.name,))
