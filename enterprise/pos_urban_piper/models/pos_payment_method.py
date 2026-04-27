from odoo import models, fields


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    is_delivery_payment = fields.Boolean(
        string='Delivery Payment',
        help='Check this if this payment method is used for online delivery orders.'
    )
    delivery_provider_id = fields.Many2one(
        'pos.delivery.provider',
        string='Delivery Provider',
        help='Responsible delivery provider for online order, e.g., UberEats, Zomato.'
    )
