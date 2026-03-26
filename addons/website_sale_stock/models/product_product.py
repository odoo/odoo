# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    stock_notification_partner_ids = fields.Many2many(
        "res.partner",
        relation="stock_notification_product_partner_rel",
        string="Back in stock Notifications",
    )

    def _has_stock_notification(self, partner):
        self.ensure_one()
        return partner in self.stock_notification_partner_ids

    def _get_max_quantity(self, website, sale_order, **kwargs):
        """Return The max quantity of a product.
        It is the difference between the quantity that's free to use and the quantity that's already
        been added to the cart.

        Note: self.ensure_one()

        :param website website: The website for which to compute the max quantity.
        :return: The max quantity of the product.
        :rtype: float | None
        """
        self.ensure_one()
        if self.is_storable and not self.allow_out_of_stock_order:
            free_qty = website._get_product_available_qty(self.sudo(), **kwargs)
            cart_qty = sale_order._get_cart_qty(self.id)
            return free_qty - cart_qty
        return None

    def _send_availability_email(self):
        products = self.search([("stock_notification_partner_ids", "!=", False)]).filtered(
            lambda p: not p._is_sold_out()
        )
        self.env["ir.cron"]._commit_progress(remaining=len(products.stock_notification_partner_ids))

        website = self.env["website"].get_current_website()
        for product_id in products.ids:
            product = self.env["product.product"].browse(product_id)
            for partner_id in product.with_context(
                # Only fetch the ids, all the other fields will be invalidated either way
                prefetch_fields=False
            ).stock_notification_partner_ids.ids:
                partner = self.env["res.partner"].browse(partner_id)
                self_ctxt = self.with_context(lang=partner.lang).with_user(website.salesperson_id)
                product_ctxt = product.with_context(lang=partner.lang)
                body_html = self_ctxt.env["mail.render.mixin"]._render_template(
                    "website_sale_stock.availability_email_body",
                    "res.partner",
                    partner.ids,
                    engine="qweb_view",
                    add_context={"product": product_ctxt},
                    options={"post_process": True},
                )[partner.id]
                full_mail = product_ctxt.env["mail.render.mixin"]._render_encapsulate(
                    "mail.mail_notification_light",
                    body_html,
                    add_context={"model_description": self_ctxt.env._("Product")},
                    context_record=product_ctxt,
                )
                mail_values = {
                    "subject": self_ctxt.env._(
                        "%(product_name)s is back in stock", product_name=product_ctxt.name
                    ),
                    "email_from": (
                        website.company_id.partner_id.email_formatted
                        or website.salesperson_id.email_formatted
                    ),
                    "email_to": partner.email_formatted,
                    "body_html": full_mail,
                }
                mail = self_ctxt.env["mail.mail"].sudo().create(mail_values)
                mail.send(raise_exception=False)

                product.stock_notification_partner_ids -= partner
                self.env["ir.cron"]._commit_progress(1)
