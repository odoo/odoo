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
from mx import DateTime
import time
import netsvc
from osv import fields, osv
from tools import config
from tools.translate import _
import tools

class multi_company_default(osv.osv):
    _name = 'multi_company.default'
    _order = 'sequence,id'
    _columns = {
         'sequence': fields.integer('Sequence'),
         'name': fields.char('Name', size=32, required=True),
         'company_id': fields.many2one('res.company', 'Main Company', required=True),
         'company_dest_id': fields.many2one('res.company', 'Default Company', required=True),
         'object_id': fields.many2one('ir.model', 'Object', required=True),
         'expression': fields.char('Expression', size=32, required=True),
 }
    _defaults = {
     'expression': lambda *a: 'True',
     'sequence': lambda *a: 1
                 }
multi_company_default()

class res_company(osv.osv):
    _inherit = 'res.company'
 
    def _company_default_get(self, cr, uid, object=False, context={}):
        proxy = self.pool.get('multi_company.default')
        ids = proxy.search(cr, uid, [('object_id.name', '=', object)])
        for rule in proxy.browse(cr, uid, ids, context):
            user = self.pool.get('res.user').browse(cr, uid, uid)
            if eval(rule.expression, {'context': context, 'user': user}):
                return rule.company_dest_id.id
        return super(res_company, self)._company_default_get(cr, uid, object, context)
 
res_company()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
