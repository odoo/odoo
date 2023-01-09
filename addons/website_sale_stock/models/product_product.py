# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
                return sum(
                    cart._get_common_product_lines(product=self).mapped('product_uom_qty')
                )
        return 0

    def _is_sold_out(self):
        combination_info = self.with_context(website_sale_stock_get_quantity=True).product_tmpl_id._get_combination_info(product_id=self.id)
        return combination_info['product_type'] == 'product' and combination_info['free_qty'] <= 0

    def _send_availability_email(self):
        for product in self.search([('stock_notification_partner_ids', '!=', False)]):
            if product._is_sold_out():
                continue
            for partner in product.stock_notification_partner_ids:
                body_html = self.env['ir.qweb']._render('website_sale_stock.availability_email_body', {"product": product})
                msg = self.env["mail.message"].sudo().new(dict(body=body_html, record_name=product.name))
                full_mail = self.env["mail.render.mixin"]._render_encapsulate(
                    "mail.mail_notification_light",
                    body_html,
                    add_context=dict(message=msg, model_description=_("Product")),
                )
                mail_values = {
                    "subject": _("The product '%(product_name)s' is now available") % {'product_name': product.name},
                    "email_from": (product.company_id.partner_id or self.env.user).email_formatted,
                    "email_to": partner.email_formatted,
                    "body_html": full_mail,
                }

                mail = self.env["mail.mail"].sudo().create(mail_values)
                mail.send(raise_exception=False)
                product.stock_notification_partner_ids -= partner
