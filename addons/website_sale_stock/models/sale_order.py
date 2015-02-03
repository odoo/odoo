# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID
from openerp.osv import osv
from openerp.tools.translate import _

class sale_order(osv.Model):
    _inherit = "sale.order"

    def _cart_update(self, cr, uid, ids, product_id=None, line_id=None, add_qty=0, set_qty=0, context=None, **kwargs):
        """
            display a out of stock warning message on cart, if customize option `Out of Stock Warning`
            is set active and product type is not `Consumable` or `Service`
         """
        values = {}
        customize_option = self.pool['ir.model.data'].xmlid_to_object(cr, SUPERUSER_ID, 'website_sale_stock.products_out_of_stock_warning')
        if line_id:
            line = self.pool['sale.order.line'].browse(cr, uid, line_id, context)
            if customize_option.active and line.product_id.type not in ('consu', 'service') and (set_qty > int(line.product_id.virtual_available)):
                values['warning'] = _('Sorry! We can only provide %s units of %s.') % (int  (line.product_id.virtual_available), line.product_id.name_get()[0][1])
                set_qty = line.product_id.virtual_available
        values.update(super(sale_order, self)._cart_update(
            cr, uid, ids, product_id, line_id, add_qty, set_qty, context, **kwargs))
        return values
