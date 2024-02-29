from odoo import api, fields, models


class PosPayment(models.Model):
    _inherit = "pos.payment"

    def _is_unallowed_payment_methods(self, payment):
        return super()._is_unallowed_payment_methods(payment) and not payment.payment_method_id.delivery_payment_method
