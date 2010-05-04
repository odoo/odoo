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

from osv import osv,fields
from operator import attrgetter
# -------------------------------------------------------------------------
# Properties
# -------------------------------------------------------------------------

class ir_property(osv.osv):
    _name = 'ir.property'

    def _models_field_get(self, cr, uid, field_key, field_value, context=None):
        get = attrgetter(field_key, field_value)

        obj = self.pool.get('ir.model.fields')
        ids = obj.search(cr, uid, [('view_load','=',1)], context=context)
        res = set()
        for o in obj.browse(cr, uid, ids, context=context):
            res.add(get(o))
        return res

    def _models_get(self, cr, uid, context=None):
        return self._models_field_get(cr, uid, 'model_id.model', 'model_id.name',
                                     context)

    def _models_get2(self, cr, uid, context=None):
        return self._models_field_get(cr, uid, 'relation', 'relation', context)


    _columns = {
        'name': fields.char('Name', size=128),
        'value': fields.reference('Value', selection=_models_get2, size=128),
#        'value': fields.char('Value', size=128),
        'res_id': fields.reference('Resource', selection=_models_get, size=128,
                                   help="If not set, act as default property"),
        'company_id': fields.many2one('res.company', 'Company'),
        'fields_id': fields.many2one('ir.model.fields', 'Fields', ondelete='cascade', required=True)
    }

    def get(self, cr, uid, name, model, res_id=False, context={}):
        cr.execute('select id from ir_model_fields where name=%s and model=%s', (name, model))
        res = cr.fetchone()
        if res:
            ucid = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
            nid = self.search(cr, uid, [('fields_id','=',res[0]),('res_id','=',res_id),('company_id','=',ucid)])
            if nid:
                d = self.browse(cr, uid, nid[0], context).value
                return (d and int(d.split(',')[1])) or False
        return False
ir_property()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

