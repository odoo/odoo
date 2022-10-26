# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_warehouse_available(self):
        self.ensure_one()
        warehouse = self.website_id._get_warehouse_available()
        if not warehouse and self.user_id and self.company_id:
            warehouse = self.user_id.with_company(self.company_id.id)._get_default_warehouse_id()
        if not warehouse:
            warehouse = self.env.user._get_default_warehouse_id()
        return warehouse

    def _compute_warehouse_id(self):
        website_orders = self.filtered('website_id')
        super(SaleOrder, self - website_orders)._compute_warehouse_id()
        for order in website_orders:
            order.warehouse_id = order._get_warehouse_available()

    def _verify_updated_quantity(self, order_line, product_id, new_qty, **kwargs):
        self.ensure_one()
        product = self.env['product.product'].browse(product_id)
        if product.type == 'product' and not product.allow_out_of_stock_order:
            product_qty_in_cart, available_qty = self._get_cart_and_free_qty(
                line=order_line, product=product, **kwargs
            )

            old_qty = order_line.product_uom_qty if order_line else 0
            added_qty = new_qty - old_qty
            total_cart_qty = product_qty_in_cart + added_qty
            if available_qty < total_cart_qty:
                allowed_line_qty = available_qty - (product_qty_in_cart - old_qty)
                if allowed_line_qty > 0:
                    if order_line:
                        order_line._set_shop_warning_stock(total_cart_qty, available_qty)
                    else:
                        self._set_shop_warning_stock(total_cart_qty, available_qty)
                else:  # 0 or negative allowed_qty
                    # if existing line: it will be deleted
                    # if no existing line: no line will be created
                    self.shop_warning = _(
                        "Some products became unavailable and your cart has been updated. We're sorry for the inconvenience.")
                return allowed_line_qty, order_line.shop_warning or self.shop_warning
        return super()._verify_updated_quantity(order_line, product_id, new_qty, **kwargs)

    def _get_cart_and_free_qty(self, line=None, product=None, **kwargs):
        """ Get cart quantity and free quantity for given product or line's product.

        Note: self.ensure_one()

        :param SaleOrderLine line: The optional line
        :param ProductProduct product: The optional product
        """
        self.ensure_one()
        if not line and not product:
            return 0, 0
        cart_qty = sum(
            self._get_common_product_lines(line, product, **kwargs).mapped('product_uom_qty')
        )
        free_qty = (product or line.product_id).with_context(warehouse=self.warehouse_id.id).free_qty
        return cart_qty, free_qty

    def _get_common_product_lines(self, line=None, product=None, **kwargs):
        """ Get the lines with the same product or line's product

        :param SaleOrderLine line: The optional line
        :param ProductProduct product: The optional product
        """
        if not line and not product:
            return self.env['sale.order.line']
        product = product or line.product_id
        return self.order_line.filtered(lambda l: l.product_id == product)

    def _set_shop_warning_stock(self, desired_qty, new_qty):
        self.ensure_one()
        self.shop_warning = _(
            'You ask for %(desired_qty)s products but only %(new_qty)s is available',
            desired_qty=desired_qty, new_qty=new_qty
        )
        return self.shop_warning

    def _get_cache_key_for_line(self, line):
        return line.product_id

    def _get_context_for_line(self, line):
        return {
            'website_sale_stock_get_quantity': True,
        }

    def _filter_can_send_abandoned_cart_mail(self):
        """ Filter sale orders on their product availability. """
        self = super()._filter_can_send_abandoned_cart_mail()
        combination_info_cache = {}

        def _are_all_product_available_for_purchase(sale_order):
            for line in sale_order.order_line:
                product = line.product_id
                if product.type != 'product':
                    continue
                cache_key = self._get_cache_key_for_line(line)
                combination_info = combination_info_cache.get(cache_key)
                if not combination_info:
                    combination_info = product.with_context(**self._get_context_for_line(line))._get_combination_info_variant(add_qty=line.product_uom_qty)
                    combination_info_cache[cache_key] = combination_info
                if not product.allow_out_of_stock_order and combination_info['free_qty'] == 0:
                    return False
            return True

        # If none of the products in the checkout are available for purchase (empty inventory, for example),
        # then the email won't be sent.
        return self.filtered(_are_all_product_available_for_purchase)
