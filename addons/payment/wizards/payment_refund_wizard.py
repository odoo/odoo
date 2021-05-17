# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo import _, api, fields, models


class PaymentRefundWizard(models.TransientModel):
    _name = "payment.refund.wizard"
    _description = "Payment Refund Wizard"

    payment_id = fields.Many2one(
        string="Payment",
        comodel_name='account.payment',
        readonly=True,
        default=lambda self: self.env.context.get('active_id'))
    payment_transaction_id = fields.Many2one(
        string="Payment Transaction",
        related='payment_id.payment_transaction_id')
    payment_amount = fields.Monetary(
        string="Payment Amount",
        related='payment_transaction_id.amount')
    refunded_amount = fields.Monetary(
        string="Refunded Amount",
        compute='_compute_refunded_amount')
    refund_amount_allowed = fields.Monetary(
        string="Maximum Refund Allowed",
        related="payment_id.refund_amount_allowed")
    refund_amount = fields.Monetary(
        string="Refund Amount",
        compute="_compute_refund_amount",
        store=True, readonly=False)
    currency_id = fields.Many2one(
        string='Currency',
        related='payment_transaction_id.currency_id')

    @api.constrains("refund_amount")
    def _check_refund_amount(self):
        for wiz in self:
            if wiz.refund_amount <= 0 or wiz.refund_amount > wiz.refund_amount_allowed:
                raise ValidationError(_("The amount to be refund has to be positive and "
                                        "can't be superior to %s.", wiz.refund_amount_allowed))

    @api.depends('payment_id', 'refund_amount_allowed')
    def _compute_refund_amount(self):
        for wizard in self:
            wizard.refund_amount = wizard.refund_amount_allowed

    @api.depends('payment_amount', 'payment_id', 'refund_amount_allowed')
    def _compute_refunded_amount(self):
        for wiz in self:
            wiz.refunded_amount = wiz.payment_amount - wiz.refund_amount_allowed

    def action_refund(self):
        for wiz in self:
            wiz.payment_transaction_id.action_refund(refund_amount=wiz.refund_amount)
