# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    pos_session_id = fields.One2many(
        'pos.session',
        'bank_statement_id',
        string='POS Sessions')
