from odoo import api, fields, models 


class PosPayment(models.Model):
    _inherit = "pos.payment"

    viva_wallet_session = fields.Char('Viva Wallet Session', help='Required to add into refund parameter in the refund order process')
