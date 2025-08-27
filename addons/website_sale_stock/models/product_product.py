# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    stock_notification_partner_ids = fields.Many2many('res.partner', relation='stock_notification_product_partner_rel', string='Back in stock Notifications')

    def _has_stock_notification(self, partner):
        self.ensure_one()
        return partner in self.stock_notification_partner_ids

    def _get_max_quantity(self, website, sale_order, **kwargs):
        """ The max quantity of a product is the difference between the quantity that's free to use
        and the quantity that's already been added to the cart.

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

    def _is_sold_out(self):
        """Return whether the product is sold out (no available quantity).

        If a product inventory is not tracked, or if it's allowed to be sold regardless
        of availabilities, the product is never considered sold out.

        :return: whether the product can still be sold
        :rtype: bool
        """
        self.ensure_one()
        if not self.is_storable or self.allow_out_of_stock_order:
            return False
        free_qty = self.env['website'].get_current_website()._get_product_available_qty(self.sudo())
        return free_qty <= 0

    def _website_show_quick_add(self):
        return not self._is_sold_out() and super()._website_show_quick_add()

    def _send_availability_email(self):
        products = self.search([('stock_notification_partner_ids', '!=', False)]).filtered(
            lambda p: not p._is_sold_out(),
        )
        self.env['ir.cron']._commit_progress(remaining=len(products.stock_notification_partner_ids))

        website = self.env['website'].get_current_website()
        for product_id in products.ids:
            product = self.env['product.product'].browse(product_id)
            for partner_id in product.with_context(
                # Only fetch the ids, all the other fields will be invalidated either way
                prefetch_fields=False,
            ).stock_notification_partner_ids.ids:
                partner = self.env['res.partner'].browse(partner_id)
                self_ctxt = self.with_context(lang=partner.lang).with_user(website.salesperson_id)
                product_ctxt = product.with_context(lang=partner.lang)
                body_html = self_ctxt.env['mail.render.mixin']._render_template(
                    'website_sale_stock.availability_email_body',
                    'res.partner',
                    partner.ids,
                    engine='qweb_view',
                    add_context={'product': product_ctxt},
                    options={'post_process': True},
                )[partner.id]
                full_mail = product_ctxt.env['mail.render.mixin']._render_encapsulate(
                    'mail.mail_notification_light',
                    body_html,
                    add_context={'model_description': self_ctxt.env._("Product")},
                    context_record=product_ctxt,
                )
                mail_values = {
                    'subject': self_ctxt.env._(
                        "%(product_name)s is back in stock", product_name=product_ctxt.name,
                    ),
                    'email_from': (
                        website.company_id.partner_id.email_formatted
                        or self_ctxt.env.user.email_formatted
                    ),
                    'email_to': partner.email_formatted,
                    'body_html': full_mail,
                }
                mail = self_ctxt.env['mail.mail'].sudo().create(mail_values)
                mail.send(raise_exception=False)

                product.stock_notification_partner_ids -= partner
                self.env['ir.cron']._commit_progress(1)

    def _to_markup_data(self, website):
        """ Override of `website_sale` to include the product availability in the offer. """
        markup_data = super()._to_markup_data(website)
        if self.is_product_variant and self.is_storable:
            if not self._is_sold_out():
                availability = 'https://schema.org/InStock'
            else:
                availability = 'https://schema.org/OutOfStock'
            markup_data['offers']['availability'] = availability
        return markup_data
