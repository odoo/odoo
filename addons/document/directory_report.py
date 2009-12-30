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

import base64

from osv import osv, fields
from osv.orm import except_orm
import urlparse

import os

class ir_action_report_xml(osv.osv):
    _name="ir.actions.report.xml"
    _inherit ="ir.actions.report.xml"

    def _model_get(self, cr, uid, ids, name, arg, context):
        res = {}
        model_pool = self.pool.get('ir.model')
        for data in self.read(cr,uid,ids,['model']):
            model = data.get('model',False)
            if model:
                model_id =model_pool.search(cr,uid,[('model','=',model)])
                if model_id:
                    res[data.get('id')] = model_id[0]
                else:
                    res[data.get('id')] = False
        return res

    def _model_search(self, cr, uid, obj, name, args):
        if not len(args):
            return []
        model_id= args[0][2]
        if not model_id:
            return []
        model = self.pool.get('ir.model').read(cr,uid,[model_id])[0]['model']
        report_id = self.search(cr,uid,[('model','=',model)])
        if not report_id:
            return [('id','=','0')]
        return [('id','in',report_id)]

    _columns={
        'model_id' : fields.function(_model_get,fnct_search=_model_search,method=True,string='Model Id'),
    }

ir_action_report_xml()
