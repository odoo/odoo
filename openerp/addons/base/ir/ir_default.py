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

    def _get_company_id(self, cr, uid, context=None):
        res = self.pool.get('res.users').read(cr, uid, [uid], ['company_id'], context=context)
        if res and res[0]['company_id']:
            return res[0]['company_id'][0]
        return False

    _defaults = {
        'company_id': _get_company_id,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
