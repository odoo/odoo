# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    warning_stock = fields.Char('Warning')

    def _check_quantity(self, product, old_qty, new_qty, line=None):
        new_qty, warning = super(SaleOrder, self)._check_quantity(product, old_qty, new_qty, line)
        if new_qty < old_qty or not (product.type == 'product' and product.inventory_availability in ['always', 'threshold']):
            return new_qty, warning

        requested_qty = new_qty - old_qty
        lines_with_product = self.order_line.filtered(lambda l: l.product_id == product)
        cart_qty = sum(lines_with_product.mapped('product_uom_qty'))
        qty_available = product.with_context(warehouse=self.warehouse_id.id).virtual_available - cart_qty
        if requested_qty > qty_available:
            new_qty = old_qty + qty_available
            warning = _('You ask for %i products but only %i is available') % (cart_qty, qty_available)
            if line:
                line.warning_stock = warning
        return new_qty, warning

    def _prepare_line_values(self, product, qty, **kwargs):
        values = super(SaleOrder, self)._prepare_line_values(product, qty, **kwargs)
        values['customer_lead'] = product.sale_delay
        return values

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
