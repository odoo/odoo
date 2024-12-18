# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import UTC

from odoo import models, fields, _
from odoo.http import request


class ProductProduct(models.Model):
    _inherit = 'product.product'

    stock_notification_partner_ids = fields.Many2many('res.partner', relation='stock_notification_product_partner_rel', string='Back in stock Notifications')

    def _has_stock_notification(self, partner):
        self.ensure_one()
        return partner in self.stock_notification_partner_ids

    def _get_cart_qty(self, website=None):
        if not self.allow_out_of_stock_order:
            website = website or self.env['website'].get_current_website()
            # When the cron is run manually, request has no attribute website, and that would cause a crash
            # so we check for it
            cart = website and request and hasattr(request, 'website') and website.sale_get_order() or None
            if cart:
                return sum(cart._get_common_product_lines(product=self).mapped('product_uom_qty'))
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

    def _get_replenishment_domain(self):
        self.ensure_one()
        return [
            ('product_id', '=', self.id),
            ('state', 'not in', ('draft', 'canceled', 'done')),
            (
                'location_dest_id',
                '=',
                (
                    (request and request.website.warehouse_id.lot_stock_id.id)
                    or self.warehouse_id.lot_stock_id.id
                ),
            ),
        ]

    def _get_gmc_items(self):
        """Compute Google Merchant Center items' fields.

        See [Google](https://support.google.com/merchants/answer/7052112)'s documentation for more
        information about each field.

        :return: a dictionary for each non-service product in this recordset.
        :rtype: list[dict]
        """
        dict_items = super()._get_gmc_items()
        moves_sudo = self.env['stock.move'].sudo()
        for product, items in dict_items.items():
            if product._is_sold_out():
                if not product.allow_out_of_stock_order:
                    items['availability'] = 'out_of_stock'
                else:
                    moves = moves_sudo.search(product._get_replenishment_domain())
                    availability_date = max(
                        (move.date for move in moves),
                        default=False,
                    )
                    if availability_date:
                        # backorder can only be used with an availability_date
                        items['availability'] = 'backorder'
                        items['availability_date'] = UTC.localize(availability_date).isoformat(
                            timespec='minutes'
                        )
        return dict_items
