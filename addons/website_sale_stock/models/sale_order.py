# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields
from odoo.tools.translate import _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    warning_stock = fields.Char('Warning')

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        values = super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)
        values = self._cart_lines_stock_update(values, **kwargs)
        return values

    def _cart_lines_stock_update(self, values, **kwargs):
        line_id = values.get('line_id')
        for line in self.order_line:
            if line.product_id.type == 'product' and not line.product_id.allow_out_of_stock_order:
                cart_qty = sum(self.order_line.filtered(lambda p: p.product_id.id == line.product_id.id).mapped('product_uom_qty'))
                if (line_id == line.id) and cart_qty > line.product_id.with_context(warehouse=self.warehouse_id.id).free_qty:
                    qty = line.product_id.with_context(warehouse=self.warehouse_id.id).free_qty - cart_qty
                    new_val = super(SaleOrder, self)._cart_update(line.product_id.id, line.id, qty, 0, **kwargs)
                    values.update(new_val)

                    # Make sure line still exists, it may have been deleted in super()_cartupdate because qty can be <= 0
                    if line.exists() and new_val['quantity']:
                        line.warning_stock = _('You ask for %s products but only %s is available') % (cart_qty, new_val['quantity'])
                        values['warning'] = line.warning_stock
                    else:
                        self.warning_stock = _("Some products became unavailable and your cart has been updated. We're sorry for the inconvenience.")
                        values['warning'] = self.warning_stock
        return values

    def _website_product_id_change(self, order_id, product_id, qty=0, **kwargs):
        res = super(SaleOrder, self)._website_product_id_change(order_id, product_id, qty=qty, **kwargs)
        product = self.env['product.product'].browse(product_id)
        res['customer_lead'] = product.sale_delay
        return res

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
