# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PaymentRefundWizard(models.TransientModel):
    _name = "payment.refund.wizard"
    _description = "Payment Refund Wizard"

    payment_id = fields.Many2one(string="Payment", comodel_name='account.payment', readonly=True,
        default=lambda self: self.env.context.get('active_id'))
    transaction_id = fields.Many2one(string="Payment Transaction",
        related='payment_id.payment_transaction_id')
    payment_amount = fields.Monetary(string="Payment Amount", related='payment_id.amount')
    refunded_amount = fields.Monetary(string="Refunded Amount", compute='_compute_refunded_amount')
    available_amount_for_refund = fields.Monetary(string="Maximum Refund Allowed",
        related='payment_id.available_amount_for_refund')
    refund_amount = fields.Monetary(string="Refund Amount", compute='_compute_refund_amount',
        store=True, readonly=False)
    currency_id = fields.Many2one(string="Currency", related='transaction_id.currency_id')
    type_refund_supported = fields.Selection(string="Type of Refund Supported",
        related='transaction_id.acquirer_id.type_refund_supported')

    @api.constrains('refund_amount')
    def _check_refund_amount(self):
        for wiz in self:
            if not 0 < wiz.refund_amount <= wiz.available_amount_for_refund:
                raise ValidationError(_(
                    "The amount to be refund has to be positive and can't be superior to %s.",
                    wiz.available_amount_for_refund
                ))

    @api.depends('available_amount_for_refund')
    def _compute_refund_amount(self):
        for wizard in self:
            wizard.refund_amount = wizard.available_amount_for_refund

    @api.depends('available_amount_for_refund')
    def _compute_refunded_amount(self):
        for wiz in self:
            wiz.refunded_amount = wiz.payment_amount - wiz.available_amount_for_refund

    def action_refund(self):
        for wiz in self:
            wiz.transaction_id.action_refund(refund_amount=wiz.refund_amount)
