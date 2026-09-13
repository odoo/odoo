from odoo import _, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    stock_notification_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="stock_notification_product_partner_rel",
        string="Back in stock Notifications",
    )

    def _has_stock_notification(self, partner):
        self.check_singleton()
        return partner in self.stock_notification_partner_ids

    def _get_max_quantity(self, website, sale_order, **kwargs):
        self.check_singleton()
        if self.is_storable and not self.allow_out_of_stock_order:
            qty_free = website._get_product_available_qty(self.sudo(), **kwargs)
            cart_qty = sale_order._get_cart_qty(self.id)
            return qty_free - cart_qty
        return None

    def _is_sold_out(self):
        self.check_singleton()
        if not self.is_storable or self.allow_out_of_stock_order:
            return False
        qty_free = (
            self.env["website"]
            .get_current_website()
            ._get_product_available_qty(self.sudo())
        )
        return qty_free <= 0

    def _website_show_quick_add(self):
        return not self._is_sold_out() and super()._website_show_quick_add()

    def _send_availability_email(self):
        for product in self.search([("stock_notification_partner_ids", "!=", False)]):
            if product._is_sold_out():
                continue
            for partner in product.stock_notification_partner_ids:
                self_ctxt = self.with_context(lang=partner.lang)
                product_ctxt = product.with_context(lang=partner.lang)
                body_html = self_ctxt.env["ir.qweb"]._render(
                    "website_sale_stock.availability_email_body",
                    {"product": product_ctxt},
                )
                full_mail = product_ctxt.env["mixin.mail.render"]._render_encapsulate(
                    "mail.mail_notification_light",
                    body_html,
                    add_context={"model_description": _("Product")},
                    context_record=product_ctxt,
                )
                context = {"lang": partner.lang}
                mail_values = {
                    "subject": _(
                        "The product '%(product_name)s' is now available",
                        product_name=product_ctxt.name,
                    ),
                    "email_from": (
                        product.company_id.partner_id or self.env.user
                    ).email_formatted,
                    "email_to": partner.email_formatted,
                    "body_html": full_mail,
                }
                del context

                mail = self_ctxt.env["mail.mail"].sudo().create(mail_values)
                mail.send(raise_exception=False)
                product.stock_notification_partner_ids -= partner  # noqa: B909  recordsets are immutable: -= rebinds, the iterator keeps the original

    def _to_markup_data(self, website):
        markup_data = super()._to_markup_data(website)
        if self.is_product_variant and self.is_storable:
            if not self._is_sold_out():
                availability = "https://schema.org/InStock"
            else:
                availability = "https://schema.org/OutOfStock"
            markup_data["offers"]["availability"] = availability
        return markup_data
