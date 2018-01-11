# coding: utf-8

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Field making the one2one relation with the payment.transaction. Mirror of the payment_id field.
    # This field is assigned during the payment.transaction create method.
    payment_transaction_id = fields.Many2one('payment.transaction', string='Transaction')

    payment_transaction_acquirer_name = fields.Char(related='payment_transaction_id.acquirer_id.name',
                                                    string='Transaction Acquirer Name')
    payment_transaction_capture = fields.Boolean(related='payment_transaction_id.capture',
                                                 string='Transaction Capture')
    payment_transaction_pending = fields.Boolean(related='payment_transaction_id.pending',
                                                 string='Transaction Pending')

    @api.multi
    def _check_payment_transaction_id(self):
        if any(not p.payment_transaction_id for p in self):
            raise ValidationError(_('Only payments linked to some transactions can be proceeded.'))

    @api.multi
    def action_capture(self):
        self._check_payment_transaction_id()
        payment_transaction_ids = self.mapped('payment_transaction_id')
        if any(not t or not t.capture for t in payment_transaction_ids):
            raise ValidationError(_('Only transactions having the capture status can be captured.'))
        payment_transaction_ids.s2s_capture_transaction()

    @api.multi
    def action_void(self):
        self._check_payment_transaction_id()
        payment_transaction_ids = self.mapped('payment_transaction_id')
        if any(not t.capture for t in payment_transaction_ids):
            raise ValidationError(_('Only transactions having the capture status can be voided.'))
        payment_transaction_ids.s2s_void_transaction()
