# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
from odoo import api, fields, models


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    pos_session_id = fields.Many2one('pos.session', string="Session", copy=False)
    account_id = fields.Many2one('account.account', related='journal_id.default_debit_account_id', readonly=True)


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    pos_statement_id = fields.Many2one('pos.order', string="POS statement", ondelete='cascade')

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            statement = self.pos_statement_id.session_id.statement_ids.filtered(lambda s: s.journal_id == self.journal_id)
            if statement:
                self.statement_id = statement.id
