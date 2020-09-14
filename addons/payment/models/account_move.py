# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    transaction_ids = fields.Many2many(
        string="Transactions", comodel_name='payment.transaction',
        relation='account_invoice_transaction_rel', column1='invoice_id', column2='transaction_id',
        readonly=True, copy=False)
    authorized_transaction_ids = fields.Many2many(
        string="Authorized Transactions", comodel_name='payment.transaction',
        compute='_compute_authorized_transaction_ids', readonly=True, copy=False)

    @api.depends('transaction_ids')
    def _compute_authorized_transaction_ids(self):
        for invoice in self:
            invoice.authorized_transaction_ids = invoice.transaction_ids.filtered(
                lambda tx: tx.state == 'authorized'
            )

    def get_portal_last_transaction(self):
        self.ensure_one()
        return self.transaction_ids._get_last()

    def payment_action_capture(self):
        self.authorized_transaction_ids._send_capture_request()

    def payment_action_void(self):
        self.authorized_transaction_ids._send_void_request()
