# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.website_sale.controllers import delivery, main


class WebsiteSaleExternalTaxCalculation(main.WebsiteSale):

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


class WebsiteSaleDelivery(delivery.Delivery):

    def _order_summary_values(self, order, **post):
        res = super()._order_summary_values(order, **post)
        try:
            order._get_and_set_external_taxes_on_eligible_records()
        except UserError as e:
            res['external_tax_error'] = str(e)
        return res
