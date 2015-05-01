# -*- coding: utf-8 -*-
from openerp import api, models, _
from openerp.addons.web.http import request

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _website_product_id_change(self, order_id, product_id, qty=0, line_id=None):
        self.ensure_one()
        values = {}
        if request.website.stock_warning_active:
            sale_order = self.browse(order_id)
            values = self.env['sale.order.line'].product_id_change_with_wh( 
                pricelist=sale_order.pricelist_id.id,
                product=product_id,
                partner_id=sale_order.partner_id.id,
                fiscal_position=sale_order.fiscal_position.id,
                qty=qty
            )
        res = super(SaleOrder, self)._website_product_id_change(order_id, product_id, qty, line_id)
        if values.get('warning'):
            product = self.env['product.product'].sudo().browse(product_id)
            res['product_uom_qty'] = product.qty_available
            if product.qty_available <= 0:
                res['warning'] = _('Sorry ! The %s is out of stock.') % (product.display_name)
            else:
                res['warning'] = _('Sorry ! Only %s units of %s are still in stock.') % (int  (product.qty_available), product.name_get()[0][1])
        return res
