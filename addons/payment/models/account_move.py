# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# TODO ANV clean

class AccountMove(models.Model):
    _inherit = 'account.move'

    transaction_ids = fields.Many2many('payment.transaction', 'account_invoice_transaction_rel', 'invoice_id', 'transaction_id',
                                       string='Transactions', copy=False, readonly=True)
    authorized_transaction_ids = fields.Many2many('payment.transaction', compute='_compute_authorized_transaction_ids',
                                                  string='Authorized Transactions', copy=False, readonly=True)

    @api.depends('transaction_ids')
    def _compute_authorized_transaction_ids(self):
        for trans in self:
            trans.authorized_transaction_ids = trans.transaction_ids.filtered(lambda t: t.state == 'authorized')

    def get_portal_last_transaction(self):
        self.ensure_one()
        return self.transaction_ids._get_last()

    def payment_action_capture(self):
        self.authorized_transaction_ids.s2s_capture_transaction()

    def payment_action_void(self):
        self.authorized_transaction_ids.s2s_void_transaction()
