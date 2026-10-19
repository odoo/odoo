from odoo import api, models, fields


class PosPayment(models.Model):
    _inherit = "pos.payment"

    viva_com_session_id = fields.Char(help="Session ID of the transaction, stored so that it can be used to refund the payment.")

    @api.model
    def _get_additional_payment_fields(self):
        return super()._get_additional_payment_fields() + ["viva_com_session_id"]
