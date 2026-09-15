# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    pos_payment_method_id = fields.Many2one(
        'pos.payment.method',
        string="POS Payment Method",
        copy=False,
    )
    pos_session_id = fields.Many2one(
        'pos.session',
        string="Session",
        copy=False,
        index='btree_not_null',
    )
