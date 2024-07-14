# -*- coding: utf-8 -*-

from odoo import _, http
from odoo.addons.website_sale.controllers import main
from odoo.exceptions import AccessError, MissingError, ValidationError


class WebsiteSale(main.WebsiteSale):

    def _get_shop_payment_errors(self, order):
        errors = super()._get_shop_payment_errors(order)
        if order.fiscal_position_id.is_taxcloud:
            try:
                order.validate_taxes_on_sales_order()
            except ValidationError:
                errors.append((
                    _("Validation Error"),
                    _("This address does not appear to be valid. Please make sure it has been filled in correctly."),
                ))
        return errors

    def _get_shop_payment_values(self, order, **kwargs):
        res = super()._get_shop_payment_values(order, **kwargs)
        res['on_payment_step'] = True
        return res

    def _update_website_sale_delivery_return(self, order, **post):
        if order and order.fiscal_position_id.is_taxcloud:
            order.validate_taxes_on_sales_order()
        return super()._update_website_sale_delivery_return(order, **post)


class PaymentPortal(main.PaymentPortal):

    @http.route()
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        """
        Recompute taxcloud sales before payment
        """
        try:
            order = self._document_check_access('sale.order', order_id, access_token)
            order.validate_taxes_on_sales_order()
        except MissingError as error:
            raise error
        except AccessError as e:
            raise ValidationError(_("The access token is invalid.")) from e

        return super().shop_payment_transaction(order_id, access_token, **kwargs)
