# -*- encoding: utf-8 -*-
############################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (C) 2008-2009 AJM Technologies S.A. (<http://www.ajm.lu). All Rights Reserved
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
############################################################################################

from osv import osv, fields
import netsvc
import time
import tools
import mx.DateTime
from tools import config
from tools.translate import _
import tools

class crm_opportunity2meeting(osv.osv_memory):
    _name = 'crm.opportunity2meeting'
    _description = 'Opportunity To Meeting'

    def action_cancel(self, cr, uid, ids, context=None):
        return {'type':'ir.actions.act_window_close'}

    def action_makeMeeting(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0], context=context)
        record_id = context and context.get('record_id', False) or False
        if record_id:
            opportunity_case_obj = self.pool.get('crm.opportunity')                
            data_obj = self.pool.get('ir.model.data')
            result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_meetings_filter')
            id = data_obj.read(cr, uid, result, ['res_id'])
            id1 = data_obj._get_id(cr, uid, 'crm', 'crm_case_calendar_view_meet')
            id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_form_view_meet')
            id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_tree_view_meet')
            if id1:
                id1 = data_obj.browse(cr, uid, id1, context=context).res_id
            if id2:
                id2 = data_obj.browse(cr, uid, id2, context=context).res_id
            if id3:
                id3 = data_obj.browse(cr, uid, id3, context=context).res_id
            opportunity = opportunity_case_obj.browse(cr, uid, record_id, context=context)
            partner_id = opportunity.partner_id and opportunity.partner_id.id or False
            name = opportunity.name
            email = opportunity.email_from
            section_id = opportunity.section_id and opportunity.section_id.id or False        
            return {            
                'name': _('Meetings'),
                'domain' : "[('user_id','=',%s)]"%(uid),  
                'context': {'default_partner_id': partner_id, 'default_section_id': section_id, 'default_email_from': email, 'default_state':'open', 'default_name':name},
                'view_type': 'form',
                'view_mode': 'calendar,form,tree',
                'res_model': 'crm.meeting',
                'view_id': False,
                'views': [(id1,'calendar'),(id2,'form'),(id3,'tree')],
                'type': 'ir.actions.act_window',
                'search_view_id': id['res_id']
                }
        else:
            return {}
                
crm_opportunity2meeting()