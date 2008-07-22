##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################

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
