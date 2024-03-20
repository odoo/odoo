from odoo import api, fields, models
from odoo.addons.payment_razorpay.const import SUPPORTED_CURRENCIES as RAZORPAY_SUPPORTED_CURRENCIES


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    is_razorpay_supported_currency = fields.Boolean(compute='_compute_is_razorpay_supported_currency')

    @api.depends('name')
    def _compute_is_razorpay_supported_currency(self):
        for currency in self:
            currency.is_razorpay_supported_currency = currency.name in RAZORPAY_SUPPORTED_CURRENCIES
