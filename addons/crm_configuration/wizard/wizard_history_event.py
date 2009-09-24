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

import wizard
import pooler
import time

def _open_history_event(self, cr, uid, data, context): 
    pool = pooler.get_pool(cr.dbname)
    data_obj = pool.get('ir.model.data')
    result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_filter')
    id = data_obj.read(cr, uid, result, ['res_id'])
    id2 = data_obj._get_id(cr, uid, 'crm_configuration', 'crm_case_calendar_section-view')
    if id2:
        id2 = data_obj.browse(cr, uid, id2, context=context).res_id     
    return {
        'name': 'History : ' +  pooler.get_pool(cr.dbname).get(data['model']).browse(cr,uid,data['ids'])[0].name,
        'view_type': 'form',
        "view_mode": 'calendar, tree, form',
        'view_id' : False,
        'views': [(id2,'calendar'),(False,'form'),(False,'tree'),(False,'graph')],
        'res_model': 'crm.case',
        'type': 'ir.actions.act_window',
        'domain': "[('case_id','=',%d)]" % (data['id']),
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