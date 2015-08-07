# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved

from openerp import fields, models


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'
    pos_session_id = fields.Many2one(
        'pos.session', string="Session", copy=False)
    account_id = fields.Many2one(
        'account.account', related='journal_id.default_debit_account_id', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True, default=lambda self: self.env.uid)


class AccountBankStatementLline(models.Model):
    _inherit = 'account.bank.statement.line'

    pos_statement_id = fields.Many2one('pos.order', string="POS statement", ondelete='cascade')
