from odoo import api, models, _
from odoo.exceptions import UserError


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    @api.ondelete(at_uninstall=False)
    def _unlink_default_payment_method(self):
        payment_method_unknown = self.env.ref('payment.payment_method_unknown')
        if payment_method_unknown in self:
            raise UserError(_("You cannot delete the default payment method."))
