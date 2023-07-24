from odoo import models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    # will be overridden.
    def payment_request_from_kiosk(self, order):
        pass
