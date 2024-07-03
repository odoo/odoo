from odoo import fields, models


class PosPaymentProvider(models.Model):
    _inherit = 'pos.payment.provider'

    code = fields.Selection(selection_add=[('paytm', 'PayTM')], ondelete={'paytm': 'set default'})
    paytm_channel_id = fields.Char(string='PayTM Channel ID', default='EDC', copy=False)
    paytm_accept_payment = fields.Selection([
        ('auto', 'Automatically'), ('manual', 'Manually')], default='auto',
        help='Choose accept payment mode: \n Manually or Automatically', copy=False)
    paytm_allowed_payment_modes = fields.Selection([
        ('all', 'All'), ('card', 'Card'), ('qr', 'QR')], default='all',
        help='Choose allow payment mode: \n All/Card or QR', copy=False)
    paytm_mid = fields.Char(string='PayTM Merchant ID', help='Go to https://business.paytm.com/ and create the merchant account', copy=False)
    paytm_merchant_key = fields.Char(string='PayTM Merchant API Key', help='Merchant/AES key \n ex: B1o6Ivjy8L1@abc9', copy=False)
