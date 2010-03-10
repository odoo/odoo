# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from mx.DateTime import now

from osv import osv, fields
import netsvc
import ir
import pooler
from tools.translate import _

class crm_opportunity2phonecall(osv.osv_memory):
    _name = 'crm.opportunity2phonecall'
    _description = 'Opportunity to Phonecall'
    _columns = {
        'name' : fields.char('Call summary', size=64, required=True, select=1),
        'user_id' : fields.many2one('res.users',"Assign To"),
        'date': fields.datetime('Date' ,required=True),
        'section_id':fields.many2one('crm.case.section','Sales Team'),

    }
    def default_get(self, cr, uid, fields, context=None):
        record_id = context and context.get('record_id', False) or False
        res = super(crm_opportunity2phonecall, self).default_get(cr, uid, fields, context=context)
        if record_id:
            opportunity = self.pool.get('crm.opportunity').browse(cr, uid, record_id, context=context)
            res['name']=opportunity.name
            res['user_id']=opportunity.user_id and opportunity.user_id.id or False
            res['section_id']=opportunity.section_id and opportunity.section_id.id or False 
        return res

    def action_cancel(self, cr, uid, ids, context=None):
        return {'type':'ir.actions.act_window_close'}

    def action_apply(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0], context=context)
        mod_obj =self.pool.get('ir.model.data') 
        result = mod_obj._get_id(cr, uid, 'crm', 'view_crm_case_phonecalls_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'])
        phonecall_case_obj = self.pool.get('crm.phonecall')
        opportunity_case_obj = self.pool.get('crm.opportunity') 
        # Select the view
        record_id = context and context.get('record_id', False) or False
        data_obj = self.pool.get('ir.model.data')
        id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_phone_tree_view')
        id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_phone_form_view')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id

        opportunites = opportunity_case_obj.browse(cr, uid, [record_id])
        for opportunity in opportunites:            
            new_case = phonecall_case_obj.create(cr, uid, {
                    'name' : opportunity.name,
                    'case_id' : opportunity.id ,
                    'user_id' : this.user_id and this.user_id.id or False,
                    'categ_id' : opportunity.categ_id and opportunity.categ_id.id or False,
                    'description' : opportunity.description or False,
                    'date' : this.date,
                    'section_id' : opportunity.section_id and opportunity.section_id.id or False,
                    'partner_id': opportunity.partner_id and opportunity.partner_id.id or False,
                    'partner_address_id':opportunity.partner_address_id and opportunity.partner_address_id.id or False,
                    'partner_phone' : opportunity.phone or (opportunity.partner_address_id and opportunity.partner_address_id.phone or False),
                    'partner_mobile' : opportunity.partner_address_id and opportunity.partner_address_id.mobile or False,
                    'priority': opportunity.priority,
                    'opportunity_id':opportunity.id
            }, context=context)
            vals = {}

            phonecall_case_obj.case_open(cr, uid, [new_case])        
            
        value = {            
            'name': _('Phone Call'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'crm.phonecall',
            'res_id' : new_case,
            'views': [(id3,'form'),(id2,'tree'),(False,'calendar'),(False,'graph')],
            'type': 'ir.actions.act_window',
            'search_view_id': res['res_id']
        }
        return value
        
    
crm_opportunity2phonecall()   