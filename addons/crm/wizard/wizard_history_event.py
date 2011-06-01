# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

import wizard
import pooler

def _open_history_event(self, cr, uid, data, context=None):
    pool = pooler.get_pool(cr.dbname)
    data_obj = pool.get('ir.model.data')
    result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_filter')
    id = data_obj.read(cr, uid, result, ['res_id'])
    id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_calendar_section-view')
    if id2:
        id2 = data_obj.browse(cr, uid, id2, context=context).res_id 
    res = ''    
    if data.get('model',False) and data.get('ids',False):           
        model_obj = pooler.get_pool(cr.dbname).get(data['model'])
        res = model_obj.browse(cr, uid, data['ids'], context=context)
        if len(res):
            res = res[0].name       
    return {
        'name': 'History : ' +  res,
        'view_type': 'form',
        "view_mode": 'calendar, tree, form',
        'view_id' : False,
        'views': [(id2,'calendar'),(False,'form'),(False,'tree'),(False,'graph')],
        'res_model': 'crm.case',
        'type': 'ir.actions.act_window',
        'domain': data.get('id',False) and "[('case_id','=',%d)]" % (data['id']) or "[]",
        'search_view_id': id['res_id'] 
    }
    
class case_history_event(wizard.interface):
    states = {
    'init': {
            'actions': [],
            'result': {'type': 'action', 'action': _open_history_event, 'state':'end'}
        }
    }
    
case_history_event('crm.case.history.events')
