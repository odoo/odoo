from odoo import models, fields

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    is_cinetpay = fields.Boolean(string="CinetPay", default=False)
