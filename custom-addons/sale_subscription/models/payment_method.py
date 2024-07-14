# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentMethod(models.Model):

    _inherit = 'payment.method'

    @api.model
    def _get_compatible_payment_methods(self, *args, sale_order_id=None, **kwargs):
        """ Override of `payment` to require tokenization support from the payment methods when
        paying for a subscription.

        :param int sale_order_id: The sales order to be paid, as a `sale.order` id.
        :return: The compatible payment methods.
        :rtype: payment.method
        """
        if sale_order_id:
            sale_order = self.env['sale.order'].browse(sale_order_id).exists()
            if sale_order.is_subscription or sale_order.subscription_id.is_subscription:
                return super()._get_compatible_payment_methods(
                    *args, force_tokenization=True, sale_order_id=sale_order_id, **kwargs
                )
        return super()._get_compatible_payment_methods(*args, sale_order_id=sale_order_id, **kwargs)
