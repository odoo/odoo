# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.sale_gelato import utils


_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # === CRUD METHODS === #

    def _prevent_mixing_gelato_and_non_gelato_products(self):
        """ Ensure that the order lines don't mix Gelato and non-Gelato products.

        This method is not a constraint and is called from the `create` and `write` methods of
        `sale.order.line` to cover the cases where adding/writing on order lines would not trigger a
        constraint check (e.g., adding products through the Catalog).

        :return: None
        :raise ValidationError: If Gelato and non-Gelato products are mixed.
        """
        for order in self:
            gelato_lines = order.order_line.filtered(lambda l: l.product_id.gelato_product_uid)
            non_gelato_lines = (order.order_line - gelato_lines).filtered(
                lambda l: l.product_id.sale_ok and l.product_id.type != 'service'
            )  # Filter out non-saleable (sections, etc.) and non-deliverable products.
            if gelato_lines and non_gelato_lines:
                raise ValidationError(
                    _("You cannot mix Gelato products with non-Gelato products in the same order."))

    # === ACTION METHODS === #

    def action_open_delivery_wizard(self):
        """ Override of `delivery` to set a Gelato delivery method by default in the wizard. """
        res = super().action_open_delivery_wizard()

        if (
            not self.env.context.get('carrier_recompute')
            and any(line.product_id.gelato_product_uid for line in self.order_line)
        ):
            gelato_delivery_method = self.env['delivery.carrier'].search(
                [('delivery_type', '=', 'gelato')], limit=1
            )
            res['context']['default_carrier_id'] = gelato_delivery_method.id
        return res

    def action_confirm(self):
        """ Override of `sale` to send the order to Gelato on confirmation. """
        res = super().action_confirm()
        for order in self.filtered(
            lambda o: any(o.order_line.product_id.mapped('gelato_product_uid'))
        ):
            order._create_order_on_gelato()
        return res

    # === BUSINESS METHODS === #

    def _create_order_on_gelato(self):
        """ Send the order creation request to Gelato and log the request result on the chatter.

        :return: None
        """
        delivery_line = self.order_line.filtered(
            lambda l: l.is_delivery and l.product_id.default_code in ('normal', 'express')
        )
        payload = {
            'orderType': 'order',
            'orderReferenceId': self.id,
            'customerReferenceId': f'Odoo Partner #{self.partner_id.id}',
            'currency': self.currency_id.name,
            'items': self._gelato_prepare_items_payload(),
            'shipmentMethodUid': delivery_line.product_id.default_code or 'cheapest',
            'shippingAddress': self.partner_shipping_id._gelato_prepare_address_payload(),
        }
        try:
            api_key = self.company_id.sudo().gelato_api_key  # In sudo mode to read on the company.
            data = utils.make_request(api_key, 'order', 'v4', 'orders', payload=payload)
        except UserError as e:
            raise UserError(_(
                "The order with reference %(order_reference)s was not sent to Gelato.\n"
                "Reason: %(error_message)s",
                order_reference=self.display_name,
                error_message=str(e),
            ))

        _logger.info("Notification received from Gelato with data:\n%s", pprint.pformat(data))
        self.message_post(
            body=_("The order has been successfully passed on Gelato."),
            author_id=self.env.ref('base.partner_root').id,
        )

    def _gelato_prepare_items_payload(self):
        """ Create the payload for the 'items' key of an 'orders' request.

        :return: The items payload.
        :rtype: dict
        """
        items_payload = []
        for gelato_line in self.order_line.filtered(lambda l: l.product_id.gelato_product_uid):
            item_data = {
                'itemReferenceId': gelato_line.product_id.id,
                'productUid': gelato_line.product_id.gelato_product_uid,
                'files': [
                    image._gelato_prepare_file_payload()
                    for image in gelato_line.product_id.product_tmpl_id.gelato_image_ids
                ],
                'quantity': int(gelato_line.product_uom_qty),
            }
            items_payload.append(item_data)
        return items_payload
