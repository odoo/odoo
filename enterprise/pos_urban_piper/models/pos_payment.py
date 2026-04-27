from odoo import api, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    @api.constrains('payment_method_id')
    def _check_payment_method_id(self):
        """
        A delivery payment method is only applicable to delivery orders, not to regular orders. So Bypass those payment method.
        """
        bypass_check_payments = self.filtered('payment_method_id.is_delivery_payment')
        super(PosPayment, self - bypass_check_payments)._check_payment_method_id()
