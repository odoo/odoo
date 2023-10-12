# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):

    def _create_transaction(self, *args, razorpay_payment_method=False, custom_create_values=None, **kwargs):
        """ Override of payment to add the sale order id in the custom create values.

        :param int sale_order_id: The sale order for which a payment id made, as a `sale.order` id
        :param dict custom_create_values: Additional create values overwriting the default ones
        :return: The result of the parent method
        :rtype: recordset of `payment.transaction`
        """
        if razorpay_payment_method:
            if custom_create_values is None:
                custom_create_values = {}
            if 'razorpay_payment_method' not in custom_create_values:
                custom_create_values['razorpay_payment_method'] = razorpay_payment_method

        return super()._create_transaction(
            *args, custom_create_values=custom_create_values, **kwargs
        )
