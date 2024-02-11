from odoo import api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    delivery_provider_ids = fields.One2many('pos.online.delivery.provider', 'payment_method_id', string='Delivery Providers', help='The delivery providers that use this payment method.')
    delivery_payment_method = fields.Boolean(default=False, compute='_compute_delivery_payment_method', store=True, help='Technical field to know if the payment method is used by a delivery service.')

    @api.depends('delivery_provider_ids')
    def _compute_delivery_payment_method(self):
        for pm in self:
            pm.delivery_payment_method = bool(pm.delivery_provider_ids)