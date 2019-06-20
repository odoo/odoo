# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def _prepare_reconciliation_move(self, move_ref):
        move_vals = super(AccountBankStatementLine, self)._prepare_reconciliation_move(move_ref)
        move_vals['l10n_in_unit_id'] = self.pos_statement_id.l10n_in_unit_id.id
        return move_vals
