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

import pickle
import osv
import pooler

def ir_set(cr, uid, key, key2, name, models, value, replace=True, isobject=False, meta=None):
    obj = pooler.get_pool(cr.dbname).get('ir.values')
    return obj.set(cr, uid, key, key2, name, models, value, replace, isobject, meta)

def ir_del(cr, uid, id):
    obj = pooler.get_pool(cr.dbname).get('ir.values')
    return obj.unlink(cr, uid, [id])

def ir_get(cr, uid, key, key2, models, meta=False, context={}, res_id_req=False):
    obj = pooler.get_pool(cr.dbname).get('ir.values')
    res = obj.get(cr, uid, key, key2, models, meta=meta, context=context, res_id_req=res_id_req)
    return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

