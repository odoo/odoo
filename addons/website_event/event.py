# -*- coding: utf-8 -*-

from openerp.osv import osv, fields

# defined for access rules
class product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'event_ticket_ids': fields.one2many('event.event.ticket', 'product_id', 'Event Tickets'),
    }


class event(osv.osv):
    _inherit = 'event.event'

    def _get_register_max(self, cr, uid, ids, field_name, arg, context=None):
        result = dict.fromkeys(ids, 0)
        for rec in self.browse(cr, uid, ids, context=context):
            result[rec.id] = sum([ep.register_max for ep in rec.event_ticket_ids])
        return result

    _columns = {
        'website_published': fields.boolean('Available in the website'),
        'description_website': fields.html('Description for the website'),
        'event_ticket_ids': fields.one2many('event.event.ticket', "event_id", "Event Ticket"),
        'organizer_id': fields.many2one('res.partner', "Orgonizer"),
        'phone': fields.related('orgonizer_id', 'phone', type='char', string='Phone'),
        'email': fields.related('orgonizer_id', 'email', type='char', string='Email'),
        'register_max': fields.function(_get_register_max,
            string='Maximum Registrations',
            help="The maximum registration level is equal to the sum of the maximum registration of event ticket." +
            "If you have too much registrations you are not able to confirm your event. (0 to ignore this rule )",
            type='integer', store=True)
    }


class event_ticket(osv.osv):
    _name = 'event.event.ticket'

    def _get_register_current(self, cr, uid, ids, field_name, arg, context=None):
        result = dict.fromkeys(ids, 0)
        for rec in self.browse(cr, uid, ids, context=context):
            result[rec.id] = sum([ep.nb_register for ep in rec.registration_ids])
        return result

    _columns = {
        'event_id': fields.many2one('event.event', "Event", required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True, domain=[("event_type_id", "!=", False)]),
        'registration_ids': fields.one2many('event.registration', 'event_ticket_id', 'Registrations'),
        'deadline': fields.date("Sales End"),
        'price': fields.float('Price'),
        'register_max': fields.integer('Maximum Registrations'),
        'register_current': fields.function(_get_register_current, string='Current Registrations', type='integer', store=True),
    }

    def onchange_product_id(self, cr, uid, ids, product_id=False, context=None):
        return {'value': {'price': self.pool.get("product.product").browse(cr, uid, product_id).list_price or 0}}


class event_registration(osv.osv):
    """Event Registration"""
    _inherit= 'event.registration'
    _columns = {
        'event_ticket_id': fields.many2one('event.event.ticket', 'Event Ticket'),
    }
