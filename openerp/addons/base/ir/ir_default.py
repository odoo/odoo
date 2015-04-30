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

from openerp.osv import fields, osv

class ir_default(osv.osv):
    _name = 'ir.default'
    _columns = {
        'field_tbl': fields.char('Object'),
        'field_name': fields.char('Object Field'),
        'value': fields.char('Default Value'),
        'uid': fields.many2one('res.users', 'Users'),
        'page': fields.char('View'),
        'ref_table': fields.char('Table Ref.'),
        'ref_id': fields.integer('ID Ref.',size=64),
        'company_id': fields.many2one('res.company','Company')
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'ir.default', context=c),
    }
