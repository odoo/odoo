# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv,fields

# -------------------------------------------------------------------------
# Properties
# -------------------------------------------------------------------------

def _models_get2(self, cr, uid, context={}):
    obj = self.pool.get('ir.model.fields')
    ids = obj.search(cr, uid, [('view_load','=',1)])
    res = []
    done = {}
    for o in obj.browse(cr, uid, ids, context=context):
        if o.relation not in done:
            res.append( [o.relation, o.relation])
            done[o.relation] = True
    return res

def _models_get(self, cr, uid, context={}):
    obj = self.pool.get('ir.model.fields')
    ids = obj.search(cr, uid, [('view_load','=',1)])
    res = []
    done = {}
    for o in obj.browse(cr, uid, ids, context=context):
        if o.model_id.id not in done:
            res.append( [o.model_id.model, o.model_id.name])
            done[o.model_id.id] = True
    return res

class ir_property(osv.osv):
    _name = 'ir.property'
    _columns = {
        'name': fields.char('Name', size=128),
        'value': fields.reference('Value', selection=_models_get2, size=128),
        'res_id': fields.reference('Resource', selection=_models_get, size=128),
        'company_id': fields.many2one('res.company', 'Company'),
        'fields_id': fields.many2one('ir.model.fields', 'Fields', ondelete='cascade', required=True)
    }
    def unlink(self, cr, uid, ids, context={}):
        if ids:
            cr.execute('delete from ir_model_fields where id in (select fields_id from ir_property where (fields_id is not null) and (id in %s))', (tuple(ids),))
        res = super(ir_property, self).unlink(cr, uid, ids, context)
        return res

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

