# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from pytz import UTC

from odoo import models, fields, _
from odoo.http import request


class ProductProduct(models.Model):
    _inherit = 'product.product'

    stock_notification_partner_ids = fields.Many2many('res.partner', relation='stock_notification_product_partner_rel', string='Back in stock Notifications')

    def _has_stock_notification(self, partner):
        self.ensure_one()
        return partner in self.stock_notification_partner_ids

    def _get_cart_qty(self, order_sudo):
        if order_sudo and not self.allow_out_of_stock_order:
            return sum(order_sudo._get_common_product_lines(product=self).mapped('product_uom_qty'))
        return 0

    def _is_sold_out(self):
        self.ensure_one()
        if not self.is_storable:
            return False
        free_qty = self.env['website'].get_current_website()._get_product_available_qty(self.sudo())
        return free_qty <= 0

    def _website_show_quick_add(self):
        return (self.allow_out_of_stock_order or not self._is_sold_out()) and super()._website_show_quick_add()

    def _send_availability_email(self):
        for product in self.search([('stock_notification_partner_ids', '!=', False)]):
            if product._is_sold_out():
                continue
            for partner in product.stock_notification_partner_ids:
                self_ctxt = self.with_context(lang=partner.lang)
                product_ctxt = product.with_context(lang=partner.lang)
                body_html = self_ctxt.env['ir.qweb']._render(
                    'website_sale_stock.availability_email_body', {'product': product_ctxt})
                msg = self_ctxt.env['mail.message'].sudo().new(dict(body=body_html, record_name=product_ctxt.name))
                full_mail = self_ctxt.env['mail.render.mixin']._render_encapsulate(
                    "mail.mail_notification_light",
                    body_html,
                    add_context=dict(message=msg, model_description=_("Product")),
                )
                context = {'lang': partner.lang}  # Use partner lang to translate mail subject below
                mail_values = {
                    "subject": _("The product '%(product_name)s' is now available", product_name=product_ctxt.name),
                    "email_from": (product.company_id.partner_id or self.env.user).email_formatted,
                    "email_to": partner.email_formatted,
                    "body_html": full_mail,
                }
                del context

                mail = self_ctxt.env['mail.mail'].sudo().create(mail_values)
                mail.send(raise_exception=False)
                product.stock_notification_partner_ids -= partner

    def _to_markup_data(self, website):
        """ Override of `website_sale` to include the product availability in the offer. """
        markup_data = super()._to_markup_data(website)
        if self.is_product_variant and self.is_storable:
            if self.allow_out_of_stock_order or not self._is_sold_out():
                availability = 'https://schema.org/InStock'
            else:
                availability = 'https://schema.org/OutOfStock'
            markup_data['offers']['availability'] = availability
        return markup_data

    def _get_availability_date(self):
        self.ensure_one()
        StockMoveSudo = self.env['stock.move'].sudo()
        moves_domain = [
            ('product_id', '=', self.id),
            ('state', 'not in', ('draft', 'cancel', 'done')),
            ('date', '>=', datetime.now()),
        ]
        stock_warehouses_ids = (
            request.website.warehouse_id.lot_stock_id.ids
            if request and request.website.warehouse_id.lot_stock_id
            else self.env['stock.warehouse'].sudo()
                     .search([('lot_stock_id', '!=', False)])
                     .mapped('lot_stock_id.id')
        )
        incoming_moves = StockMoveSudo.search(
            moves_domain + [('location_dest_id', 'in', stock_warehouses_ids)],
            order='date'
        )
        outgoing_moves = StockMoveSudo.search(
            moves_domain + [('location_id', 'in', stock_warehouses_ids)],
            order='date'
        )

        availability_date = datetime.max
        available_qty = 0
        i, j = 0, 0
        while i < len(incoming_moves) or j < len(outgoing_moves):
            move_date, qty, (ip, jp) = min(
                (incoming_moves[i].date, incoming_moves[i].product_qty, (1, 0))
                if i < len(incoming_moves)
                else (datetime.max,),
                (outgoing_moves[j].date, -outgoing_moves[j].product_qty, (0, 1))
                if j < len(outgoing_moves)
                else (datetime.max,),
            )
            available_qty += qty
            if available_qty > 0:
                availability_date = min(availability_date, move_date)
            else:
                availability_date = datetime.max
            i += ip
            j += jp
        return availability_date if available_qty > 0 else False

    def _get_gmc_items(self):
        """Compute Google Merchant Center items' fields.

        See [Google](https://support.google.com/merchants/answer/7052112)'s documentation for more
        information about each field.

        :return: a dictionary for each non-service product in this recordset.
        :rtype: list[dict]
        """
        dict_items = super()._get_gmc_items()
        for product, items in dict_items.items():
            if product._is_sold_out():
                if not product.allow_out_of_stock_order:
                    items['availability'] = 'out_of_stock'
                else:
                    availability_date = product._get_availability_date()
                    if availability_date:
                        # backorder can only be used with an availability_date
                        items['availability'] = 'backorder'
                        items['availability_date'] = UTC.localize(availability_date).isoformat(
                            timespec='minutes'
                        )
        return dict_items
