# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import api, models


class PaymentLinkWizard(models.TransientModel):
    _inherit = 'payment.link.wizard'
    _description = 'Generate Sales Payment Link'

    def _get_payment_provider_available(self, res_model, res_id, **kwargs):
        """ Select and return the providers matching the criteria.

        :param str res_model: active model
        :param int res_id: id of 'active_model' record
        :return: The compatible providers
        :rtype: recordset of `payment.provider`
        """
        if res_model == 'sale.order':
            kwargs['sale_order_id'] = res_id
        return super()._get_payment_provider_available(**kwargs)

    def _get_additional_link_values(self):
        """ Override of `payment` to add `sale_order_id` to the payment link values.

        The other values related to the sales order are directly read from the sales order.

        Note: self.ensure_one()

        :return: The additional payment link values.
        :rtype: dict
        """
        res = super()._get_additional_link_values()
        if self.res_model != 'sale.order':
            return res

        # Order-related fields are retrieved in the controller
        return {
            'sale_order_id': self.res_id,
        }
