# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
from openerp import SUPERUSER_ID

# defined for access rules
class product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'event_ticket_ids': fields.one2many('event.event.ticket', 'product_id', 'Event Tickets'),
    }


class event(osv.osv):
    _inherit = 'event.event'
    _columns = {
        'website_published': fields.boolean('Available in the website'),
        'description_website': fields.html('Description for the website'),
    }

class event_event(osv.osv):
    _inherit = "event.event"

    def google_map_img(self, cr, uid, ids, zoom=8, width=298, height=298, context=None):
        partner = self.browse(cr, uid, ids[0], context=context)
        if partner.address_id:
            return self.browse(cr, SUPERUSER_ID, ids[0], context=context).address_id.google_map_img()

    def google_map_link(self, cr, uid, ids, zoom=8, context=None):
        partner = self.browse(cr, uid, ids[0], context=context)
        if partner.address_id:
            return self.browse(cr, SUPERUSER_ID, ids[0], context=context).address_id.google_map_link()

class sale_order_line(osv.osv):
    _inherit = "sale.order.line"
 
    def _recalculate_product_values(self, cr, uid, ids, product_id=None, context=None):
        if not ids:
            return super(sale_order_line, self)._recalculate_product_values(cr, uid, ids, product_id, context=context)
        
        order_line = self.browse(cr, uid, ids[0], context=context)
        product = product_id and self.pool.get('product.product').browse(cr, uid, product_id, context=context) or order_line.product_id
        res = super(sale_order_line, self)._recalculate_product_values(cr, uid, ids, product.id, context=context)
        if product.event_type_id and order_line.event_ticket_id and order_line.event_ticket_id.price != product.lst_price:
            res.update({'price_unit': order_line.event_ticket_id.price})

        return res
