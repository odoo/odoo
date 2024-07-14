# coding: utf-8
from odoo import _
from odoo.exceptions import UserError

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleExternalTaxCalculation(WebsiteSale):

    def _get_shop_payment_errors(self, order):
        errors = super()._get_shop_payment_errors(order)
        try:
            order._get_and_set_external_taxes_on_eligible_records()
        except UserError as e:
            errors.append(
                (_("Validation Error"),
                 _("This address does not appear to be valid. Please make sure it has been filled in correctly. Error details: %s", e))
            )
        return errors

    def _get_shop_payment_values(self, order, **kwargs):
        res = super()._get_shop_payment_values(order, **kwargs)
        res['on_payment_step'] = True
        return res

    def _update_website_sale_delivery_return(self, order, **post):
        order._get_and_set_external_taxes_on_eligible_records()
        return super()._update_website_sale_delivery_return(order, **post)
