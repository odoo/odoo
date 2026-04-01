from odoo import models, fields


class PosPayment(models.Model):
    _inherit = "pos.payment"

    viva_com_session_id = fields.Char(help="Session ID of the transaction, stored so that it can be used to refund the payment.")
