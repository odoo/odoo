# -*- coding: utf-8 -*-
from openerp.osv import orm
from openerp import SUPERUSER_ID


class Website(orm.Model):
    _inherit = 'website'

    def _ecommerce_create_quotation(self, cr, uid, context=None):
        order_id = super(Website, self)._ecommerce_create_quotation(cr, uid, context=context)
        order = self.pool['sale.order'].browse(cr, SUPERUSER_ID, order_id, context=context)
        self.pool['sale.order']._check_carrier_quotation(cr, uid, order, force_carrier_id=None, context=context)
        return order_id

    def _ecommerce_add_product_to_cart(self, cr, uid, product_id=0, order_line_id=0, number=1, set_number=-1, context=None):
        quantity = super(Website, self)._ecommerce_add_product_to_cart(cr, uid,
            product_id=product_id, order_line_id=order_line_id, number=number, set_number=set_number,
            context=context)
        order = self.ecommerce_get_current_order(cr, uid, context=context)
        self.pool['sale.order']._check_carrier_quotation(cr, uid, order, force_carrier_id=None, context=context) and quantity or None
        return quantity
