# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class event(osv.osv):
    _inherit = 'event.event'
    _columns = {
        'website_published': fields.boolean('Available in the website'),
        'description_website': fields.html('Description for the website'),
        'product_ids': fields.one2many('event.event.product', "event_id", "Event"),
    }


class event_product(osv.osv):
    _name = 'event.event.product'
    _columns = {
        'event_id': fields.many2one('event.event', "Event"),
        'product_id': fields.many2one('product.product', 'Product'),
        'price': fields.float('Price'),
        'qty': fields.integer('Current Registrations', readonly=True),
        'max_qty': fields.integer('Maximum Registrations'),
    }
