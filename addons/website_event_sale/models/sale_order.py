# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

# defined for access rules
class sale_order(osv.Model):
    _inherit = "sale.order"

    def _cart_find_product_line(self, cr, uid, ids, product_id=None, line_id=None, context=None, **kwargs):
        line_ids = super(sale_order, self)._cart_find_product_line(cr, uid, ids, product_id, line_id, context=context)
        if line_id:
            return line_ids
        for so in self.browse(cr, uid, ids, context=context):
            domain = [('id', 'in', line_ids)]
            if context.get("event_ticket_id"):
                domain += [('event_ticket_id', '=', context.get("event_ticket_id"))]
            return self.pool.get('sale.order.line').search(cr, SUPERUSER_ID, domain, context=context)

    def _website_product_id_change(self, cr, uid, ids, order_id, product_id, qty=0, line_id=None, context=None):
        values = super(sale_order, self)._website_product_id_change(
            cr, uid, ids, order_id, product_id,
            qty=qty, line_id=line_id, context=context)

        event_ticket_id = None
        if context.get("event_ticket_id"):
            event_ticket_id = context.get("event_ticket_id")
        elif line_id:
            line = self.pool.get('sale.order.line').browse(cr, SUPERUSER_ID, line_id, context=context)
            if line.event_ticket_id:
                event_ticket_id = line.event_ticket_id.id
        else:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            if product.event_ticket_ids:
                event_ticket_id = product.event_ticket_ids[0].id

        if event_ticket_id:
            order = self.pool['sale.order'].browse(cr, SUPERUSER_ID, order_id, context=context)
            ticket = self.pool.get('event.event.ticket').browse(cr, uid, event_ticket_id, context=dict(context, pricelist=order.pricelist_id.id))
            if product_id != ticket.product_id.id:
                raise osv.except_osv(_('Error!'),_("The ticket doesn't match with this product."))

            values['product_id'] = ticket.product_id.id
            values['event_id'] = ticket.event_id.id
            values['event_ticket_id'] = ticket.id
            values['price_unit'] = ticket.price_reduce or ticket.price
            values['name'] = "%s\n%s" % (ticket.event_id.display_name, ticket.name)

        return values
