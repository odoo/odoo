# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, _


class ProductWishlist(models.Model):
    _inherit = "product.wishlist"

    stock_notification = fields.Boolean(default=False, required=True)

    def _add_to_wishlist(self, pricelist_id, currency_id, website_id, price, product_id, partner_id=False):
        wish = super()._add_to_wishlist(
            pricelist_id=pricelist_id,
            currency_id=currency_id,
            website_id=website_id,
            price=price,
            product_id=product_id,
            partner_id=partner_id,
        )
        wish['stock_notification'] = wish.product_id._is_sold_out()

        return wish

    def _send_availability_email(self):
        to_notify = self.env['product.wishlist'].search([('stock_notification', '=', True)])

        if not to_notify:
            return

        notified = self.env['product.wishlist']

        # cannot group by product_id because it depend of website_id -> warehouse_id
        tmpl = self.env.ref("website_sale_stock_wishlist.availability_email_body")
        for wishlist in to_notify:
            product = wishlist.with_context(website_id=wishlist.website_id.id).product_id
            if not product._is_sold_out():
                body_html = tmpl._render({"wishlist": wishlist})
                msg = self.env["mail.message"].sudo().new(dict(body=body_html, record_name=product.name))
                full_mail = self.env["mail.render.mixin"]._render_encapsulate(
                    "mail.mail_notification_light",
                    body_html,
                    add_context=dict(message=msg, model_description=_("Wishlist")),
                )
                mail_values = {
                    "subject": _("The product '%(product_name)s' is now available") % {'product_name': product.name},
                    "email_from": (product.company_id.partner_id or self.env.user).email_formatted,
                    "email_to": wishlist.partner_id.email_formatted,
                    "body_html": full_mail,
                }

                mail = self.env["mail.mail"].sudo().create(mail_values)
                mail.send(raise_exception=False)
                notified += wishlist
        notified.stock_notification = False
