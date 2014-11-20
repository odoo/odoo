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
        values = super(sale_order,self)._website_product_id_change(cr, uid, ids, order_id, product_id, qty=qty, line_id=line_id, context=None)

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
            ticket = self.pool.get('event.event.ticket').browse(cr, uid, event_ticket_id, context=context)
            if product_id != ticket.product_id.id:
                raise osv.except_osv(_('Error!'),_("The ticket doesn't match with this product."))

            values['product_id'] = ticket.product_id.id
            values['event_id'] = ticket.event_id.id
            values['event_ticket_id'] = ticket.id
            values['price_unit'] = ticket.price
            values['name'] = "%s: %s" % (ticket.event_id.name, ticket.name)

        return values

    def _cart_update(self, cr, uid, ids, product_id=None, line_id=None, add_qty=0, set_qty=0, context=None, **kwargs):
        sol_obj = self.pool.get('sale.order.line')
        if line_id:
            order_line = sol_obj.browse(cr, uid, line_id, context=context)
            old_qty = int(order_line.product_uom_qty)
        values = super(sale_order,self)._cart_update(cr, uid, ids, product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, context=context, **kwargs)
        new_qty = int(values['quantity'])
        if line_id and new_qty:
            if order_line.event_id.id:
                if old_qty > new_qty:
                    attendee_ids = []
                    attendee_list = self.pool.get('event.registration').search_read(cr, uid, [
                        ('origin', '=', order_line.order_id.name),
                        ('event_ticket_id', '=', order_line.event_ticket_id.id)], context=context)
                    for attendee in attendee_list:
                        attendee_ids.append(attendee['id'])
                    for i in range(0, (old_qty - new_qty)):
                        self._unlink_attendee(cr, uid, [attendee_ids[-1]], context=context)
                        attendee_ids.pop(-1)
                else:
                    new_qty = new_qty
                    if order_line.event_ticket_id and set_qty > order_line.event_ticket_id.seats_available:
                        sol_obj.write(cr, SUPERUSER_ID, line_id, {'product_uom_qty': order_line.event_ticket_id.seats_available}, context=context)
                        values['available_qty'] = order_line.event_ticket_id.seats_available
                        order_line_count = sol_obj.search_count(cr, uid, [('order_id', '=', order_line.order_id.id)], context=context)
                        new_qty = order_line.event_ticket_id.seats_available
                        if order_line_count > 1:
                             values['warning'] = 'Sorry, The ' + order_line.event_ticket_id.name + ' tickets for ' + order_line.event_id.name +' are sold out.'
                        else:
                            values['warning'] = 'Sorry, This event is sold out.'
                    for i in range(0, (new_qty - old_qty)):
                        self._create_attendee(cr, uid, order_line, context=context)
        return values

    def _unlink_attendee(self, cr, uid, attendee_id, context=None):
        self.pool.get('event.registration').unlink(cr, uid, attendee_id, context=context)
        return True

    def _create_attendee(self,cr, uid, order_line, context=None):
        self.pool.get('event.registration').create(cr, uid, {
            'event_id': order_line.event_id.id,
            'origin': order_line.order_id.name,
            'event_ticket_id': order_line.event_ticket_id.id,
            'partner_id': order_line.order_id.partner_id.id,
            }, context=context)
        return True
