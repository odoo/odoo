# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    use_sale_order_payment = fields.Boolean(
        string='Use SO Payment',
        help="When enabled, this payment method represents an online payment already "
         "collected on a Sale Order. No actual payment is collected at the Point of Sale."
    )

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['use_sale_order_payment']

    @api.ondelete(at_uninstall=True)
    def _unlink_if_sale_order_payment_method(self):
        if any(pm.use_sale_order_payment for pm in self):
            raise ValidationError(
                _('You cannot delete this payment method because it is reserved for prepaid sale order payments.')
            )
