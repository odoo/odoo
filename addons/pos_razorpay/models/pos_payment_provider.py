from odoo import fields, models


class PosPaymentProvider(models.Model):
    _inherit = 'pos.payment.provider'

    code = fields.Selection(selection_add=[('razorpay', 'Razorpay')], ondelete={'razorpay': 'set default'})
    razorpay_allowed_payment_modes = fields.Selection([
        ('all', 'All'), ('card', 'Card'), ('upi', 'UPI'), ('bharatqr', 'BHARATQR')], default='all',
        help='Choose allow payment mode: \n All/Card/UPI or QR', copy=False)
    razorpay_username = fields.Char(string='Razorpay Username', help='Username(Device Login) \n ex: 1234500121', copy=False)
    razorpay_api_key = fields.Char(
        string='Razorpay API Key',
        help='Used when connecting to Razorpay: https://razorpay.com/docs/payments/dashboard/account-settings/api-keys/', copy=False)
