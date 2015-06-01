# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields

def referencable_models(self, cr, uid, context=None):
    obj = self.pool.get('res.request.link')
    ids = obj.search(cr, uid, [], context=context)
    res = obj.read(cr, uid, ids, ['object', 'name'], context)
    return [(r['object'], r['name']) for r in res]

class res_request_link(osv.osv):
    _name = 'res.request.link'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'object': fields.char('Object', required=True),
        'priority': fields.integer('Priority'),
    }
    _defaults = {
        'priority': 5,
    }
    _order = 'priority'
