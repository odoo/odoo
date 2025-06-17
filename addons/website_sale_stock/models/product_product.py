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
        mail_template = self.env.ref('website_sale_stock.stock_availability_email')
        for product in self.search([('stock_notification_partner_ids', '!=', False)]):
            if product._is_sold_out():
                continue
            for partner in product.stock_notification_partner_ids:
                mail_template.with_context(
                    partner=partner, lang=partner.lang,
                ).send_mail(
                    product.id, email_values={'email_to': partner.email_formatted},
                )
            product.stock_notification_partner_ids = False

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

    def _prepare_gmc_stock_info(self):
        """ Override of `website_sale` to check the stock level if the current product cannot be out
        of stock.

        Note: self.ensure_one()
        """
        gmc_info = super()._prepare_gmc_stock_info()
        if self._is_sold_out():
            gmc_info['availability'] = 'out_of_stock'
        return gmc_info
