# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route

from odoo.addons.website_sale.controllers import main as website_sale_portal
from odoo.addons.website_sale.controllers.variant import WebsiteSaleVariantController


class WebsiteSaleRentingVariantController(WebsiteSaleVariantController):

    @route()
    def get_combination_info_website(self, *args, **kwargs):
        res = super().get_combination_info_website(*args, **kwargs)
        res['is_combination_possible'] = res.get('is_combination_possible', True) and res.get('is_plan_possible', True)
        return res


class WebsiteSale(website_sale_portal.WebsiteSale):

    def _get_shop_payment_values(self, order, **kwargs):
        """ Override of `website_sale` to specify whether the sales order is a subscription.

        :param sale.order order: The sales order being paid.
        :param dict kwargs: Locally unused keywords arguments.
        :return: The payment-specific values.
        :rtype: dict
        """
        is_subscription = order.is_subscription or order.subscription_id.is_subscription
        return {
            **super()._get_shop_payment_values(order, **kwargs),
            'is_subscription': is_subscription,
        }
