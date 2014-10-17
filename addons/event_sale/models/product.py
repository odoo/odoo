# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class product_template(osv.osv):
    _inherit = 'product.template'
    _columns = {
        'event_ok': fields.boolean('Event Subscription', help='Determine if a product needs to create automatically an event registration at the confirmation of a sales order line.'),
        'event_type_id': fields.many2one('event.type', 'Type of Event', help='Select event types so when we use this product in sales order lines, it will filter events of this type only.'),
    }

    def onchange_event_ok(self, cr, uid, ids, type, event_ok, context=None):
        if event_ok:
            return {'value': {'type': 'service'}}
        return {}


class product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'event_ticket_ids': fields.one2many('event.event.ticket', 'product_id', 'Event Tickets'),
    }

    def onchange_event_ok(self, cr, uid, ids, type, event_ok, context=None):
        """ Redirection, inheritance mechanism hides the method on the model """
        if event_ok:
            return {'value': {'type': 'service'}}
        return {}
