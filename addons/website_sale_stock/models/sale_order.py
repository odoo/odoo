# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    warning_stock = fields.Char('Warning')

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
            available_qty = product.with_context(warehouse=self.warehouse_id.id).free_qty
            product_qty_in_cart = sum(
                self.order_line.filtered(
                    lambda p: p.product_id.id == product_id
                ).mapped('product_uom_qty')
            )

            old_qty = order_line.product_uom_qty if order_line else 0
            added_qty = new_qty - old_qty

            if available_qty < (product_qty_in_cart + added_qty):
                allowed_line_qty = available_qty - (product_qty_in_cart - old_qty)
                if allowed_line_qty > 0:
                    warning = _(
                        'You ask for %s products but only %s is available',
                        product_qty_in_cart + added_qty,
                        available_qty,
                    )
                    if order_line:
                        order_line.warning_stock = warning
                    else:
                        self.warning_stock = warning
                else:  # 0 or negative allowed_qty
                    # if existing line: it will be deleted
                    # if no existing line: no line will be created
                    self.warning_stock = _(
                        "Some products became unavailable and your cart has been updated. We're sorry for the inconvenience.")
                return allowed_line_qty, order_line.warning_stock or self.warning_stock

        return super()._verify_updated_quantity(order_line, product_id, new_qty, **kwargs)

    def _get_stock_warning(self, clear=True):
        self.ensure_one()
        warn = self.warning_stock
        if clear:
            self.warning_stock = ''
        return warn


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warning_stock = fields.Char('Warning')

    def _get_stock_warning(self, clear=True):
        self.ensure_one()
        warn = self.warning_stock
        if clear:
            self.warning_stock = ''
        return warn
