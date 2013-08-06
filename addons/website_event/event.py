# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class event(osv.osv):
    _inherit = 'event.event'
    _columns = {
        'website_published': fields.boolean('Available in the website'),
        'description_website': fields.html('Description for the website'),
        'product_ids': fields.one2many('event.event.product', "event_id", "Event"),
        'organizer_id': fields.many2one('res.partner', "Orgonizer"),
        'phone': fields.related('orgonizer_id', 'phone', type='char', string='Phone'),
        'email': fields.related('orgonizer_id', 'email', type='char', string='Email'),
    }


class event_product(osv.osv):
    _name = 'event.event.product'
    _columns = {
        'deadline': fields.date("Sales End"),
        'event_id': fields.many2one('event.event', "Event"),
        'product_id': fields.many2one('product.product', 'Product', domain=[("event_type_id", "!=", False)]),
        'price': fields.float('Price'),
        'qty': fields.integer('Current Registrations', readonly=True),
        'max_qty': fields.integer('Maximum Registrations'),
    }

class product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'event_product_ids': fields.one2many('event.event.product', 'product_id', 'Linked event product'),
    }
