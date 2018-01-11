# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

