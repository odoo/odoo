# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.http import request

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _website_product_id_change(self, order_id, product_id, qty=0):
        self.ensure_one()
        values = {}
        if request.website.stock_warning_active:
            sale_order = self.browse(order_id)
            order_line = self.env['sale.order.line'].new({
                'product_id' : product_id,
                'product_uom_qty': qty,
                'order_id': order_id,
                'product_uom': self.env['product.product'].browse(product_id).uom_id
            })
            values = order_line._onchange_product_id_check_availability()
        res = super(SaleOrder, self)._website_product_id_change(order_id, product_id, qty)
        if values.get('warning'):
            product = self.env['product.product'].sudo().browse(product_id)
            res['product_uom_qty'] = product.virtual_available
            if product.virtual_available <= 0:
                res['message'] = _('Sorry ! The %s is out of stock.') % (product.display_name)
                res['message_type'] = 'danger'
            else:
                res['message'] = _('Sorry ! Only %d units of %s are still in stock.') % (product.virtual_available, product.display_name)
                res['message_type'] = 'warning'
        return res
