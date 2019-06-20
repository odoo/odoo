# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    l10n_in_unit_id = fields.Many2one('res.partner', string="Operating Unit", ondelete="restrict",
        default=lambda self: self.env.user._get_default_unit())

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        res = super(AccountBankStatement, self).onchange_journal_id()
        self.l10n_in_unit_id = self.journal_id.l10n_in_unit_id or self.env.user._get_default_unit()
        return res

class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _prepare_reconciliation_move(self, move_ref):
        data = super(AccountBankStatementLine, self)._prepare_reconciliation_move(move_ref)
        data['l10n_in_unit_id'] = self.statement_id.l10n_in_unit_id.id
        return data
