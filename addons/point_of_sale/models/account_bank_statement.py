# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    pos_session_id = fields.Many2one('pos.session', string="Session", copy=False)
    account_id = fields.Many2one('account.account', related='journal_id.default_debit_account_id', readonly=True)

    def check_confirm_bank(self):
        for bs in self:
            if bs.pos_session_id.state  in ('opened', 'closing_control') and bs.state == 'open':
                raise UserError(_("You can't validate a bank statement that is used in an opened Session of a Point of Sale."))
        return super( AccountBankStatement, self).check_confirm_bank()


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    pos_statement_id = fields.Many2one('pos.order', string="POS statement", ondelete='cascade')
