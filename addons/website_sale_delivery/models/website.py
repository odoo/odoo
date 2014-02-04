# -*- coding: utf-8 -*-
from openerp.osv import orm
from openerp import SUPERUSER_ID


class Website(orm.Model):
    _inherit = 'website'

    def _ecommerce_create_quotation(self, cr, uid, context=None):
        order_id = super(Website, self)._ecommerce_create_quotation(cr, uid, context=context)
        order = self.pool['sale.order'].browse(cr, SUPERUSER_ID, order_id, context=context)
        self._check_carrier_quotation(cr, uid, order, force_carrier_id=None, context=context)
        return order_id

    def _ecommerce_add_product_to_cart(self, cr, uid, product_id=0, order_line_id=0, number=1, set_number=-1, context=None):
        quantity = super(Website, self)._ecommerce_add_product_to_cart(cr, uid,
            product_id=product_id, order_line_id=order_line_id, number=number, set_number=set_number,
            context=context)
        order = self.ecommerce_get_current_order(cr, uid, context=context)
        return self._check_carrier_quotation(cr, uid, order, force_carrier_id=None, context=context) and quantity or None

    def _check_carrier_quotation(self, cr, uid, order, force_carrier_id=None, context=None):
        # check to add or remove carrier_id
        carrier_id = False
        for line in order.website_order_line:
            if line.product_id.type != "service":
                carrier_id = True
                break

        if not carrier_id:
            order.write({'carrier_id': None}, context=context)
            self.pool['sale.order']._delivery_unset(cr, SUPERUSER_ID, order, context=context)
            return True
        else: 
            if order.carrier_id:
                self.pool['sale.order']._delivery_unset(cr, SUPERUSER_ID, order, context=context)

            carrier_ids = self.pool.get('delivery.carrier').search(cr, uid, [('website_published','=',True)], context=context)
            carrier_id = force_carrier_id or (carrier_ids and carrier_ids[0])
            order.write({'carrier_id': carrier_id}, context=context)
            #If carrier_id have no grid, we don't have delivery !
            if carrier_id:
                order.delivery_set(context=context)
            else:
                self.pool['sale.order']._delivery_unset(cr, SUPERUSER_ID, order, context=context)

        return bool(carrier_id)
