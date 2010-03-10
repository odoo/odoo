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

class crm_lead2opportunity(osv.osv_memory):
    _name = 'crm.lead2opportunity'
    _description = 'Lead To Opportunity'

    def action_cancel(self, cr, uid, ids, context=None):
        return {'type':'ir.actions.act_window_close'}

    def action_apply(self, cr, uid, ids, context=None):
        
        this = self.browse(cr, uid, ids[0], context=context)
        value={}
        record_id = context and context.get('record_id', False) or False
        if record_id:
            for case in self.pool.get('crm.lead').browse(cr, uid, record_id, context=context):
                 if case.state in ['done', 'cancel']:       
                            raise osv.except_osv(_("Warning"),
                                                 _("Closed/Cancelled Phone Call Could not convert into Opportunity"))
                 else:
                    data_obj = self.pool.get('ir.model.data')
                    result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_opportunities_filter')
                    res = data_obj.read(cr, uid, result, ['res_id'])
                    
            
                    id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_form_view_oppor')
                    id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_tree_view_oppor')
                    if id2:
                        id2 = data_obj.browse(cr, uid, id2, context=context).res_id
                    if id3:
                        id3 = data_obj.browse(cr, uid, id3, context=context).res_id
            
                    lead_case_obj = self.pool.get('crm.lead')
                    opportunity_case_obj =self. pool.get('crm.opportunity')        
                    new_opportunity_id = opportunity_case_obj.create(cr, uid, {            
                            'name': this.name,
                            'planned_revenue': this.planned_revenue,
                            'probability': this.probability,
                            'partner_id': case.partner_id and case.partner_id.id or False ,
                            'section_id':case.section_id and case.section_id.id or False,
                            'description':case.description or False,
                            'date_deadline': case.date_deadline or False,
                            'partner_address_id':case.partner_address_id and case.partner_address_id.id or False ,
                            'priority': case.priority,
                            'phone': case.phone,                
                            'email_from': case.email_from
                        })       
                        
                    new_opportunity = opportunity_case_obj.browse(cr, uid, new_opportunity_id)
                    vals = {
                            'partner_id': this.partner_id and this.partner_id.id or False,                
                            }
                    if not case.opportunity_id:
                            vals.update({'opportunity_id' : new_opportunity.id})
            
                    lead_case_obj.write(cr, uid, [case.id], vals)
                    lead_case_obj.case_close(cr, uid, [case.id])
                    opportunity_case_obj.case_open(cr, uid, [new_opportunity_id])
                    
            value = {            
                        'name': _('Opportunity'),
                        'view_type': 'form',
                        'view_mode': 'form,tree',
                        'res_model': 'crm.opportunity',
                        'res_id': int(new_opportunity_id),
                        'view_id': False,
                        'views': [(id2,'form'),(id3,'tree'),(False,'calendar'),(False,'graph')],
                        'type': 'ir.actions.act_window',
                        'search_view_id': res['res_id'] 
                    }
        return value
    _columns = {
        'name' : fields.char('Opportunity Summary', size=64, required=True, select=1),
        'probability': fields.float('Success Probability'),
        'planned_revenue': fields.float('Expected Revenue'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
    }
    def default_get(self, cr, uid, fields, context=None):
        record_id = context and context.get('record_id', False) or False
        res = super(crm_lead2opportunity, self).default_get(cr, uid, fields, context=context)
        if record_id:
            for lead in self.pool.get('crm.lead').browse(cr, uid, record_id, context=context):
                res['name']= lead.partner_name
                res['partner_id']=lead.partner_id and lead.partner_id.id or False
        return res
    
crm_lead2opportunity()