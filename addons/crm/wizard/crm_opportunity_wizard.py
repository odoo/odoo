# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

from mx.DateTime import now

import wizard
import netsvc
import ir
import pooler
import time

from tools.translate import _

class opportunity2phonecall(wizard.interface):
    case_form = """<?xml version="1.0"?>
                <form string="Schedule Phone Call">
                    <separator string="Phone Call Description" colspan="4" />
                    <newline />
                    <field name='user_id' />
                    <field name='deadline' />
                    <newline />
                    <field name='note' colspan="4"/>
                    <newline />
                    <field name='section_id' />    
                    <field name='category_id' domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.phonecall')]"/>
                </form>"""

    case_fields = {
        'user_id' : {'string' : 'Assign To', 'type' : 'many2one', 'relation' : 'res.users'},
        'deadline' : {'string' : 'Planned Date', 'type' : 'datetime' ,'required' :True},
        'note' : {'string' : 'Goals', 'type' : 'text'},
        'category_id' : {'string' : 'Category', 'type' : 'many2one', 'relation' : 'crm.case.categ', 'required' :True},
        'section_id' : {'string' : 'Section', 'type' : 'many2one', 'relation' : 'crm.case.section'},
        
    }
    def _default_values(self, cr, uid, data, context):
        case_obj = pooler.get_pool(cr.dbname).get('crm.opportunity')        
        categ_id = pooler.get_pool(cr.dbname).get('crm.case.categ').search(cr, uid, [('name','=','Outbound')])            
        case = case_obj.browse(cr, uid, data['id'])
        if case.state != 'open':
            raise wizard.except_wizard(_('Warning !'),
                _('Opportunity should be in \'Open\' state before converting to Phone Call.'))
            return {}
        return {
                'user_id' : case.user_id and case.user_id.id,
                'category_id' : categ_id and categ_id[0] or case.categ_id and case.categ_id.id,
                'section_id' : case.section_id and case.section_id.id or False,
                'note' : case.description
               }

    def _doIt(self, cr, uid, data, context):
        form = data['form']
        pool = pooler.get_pool(cr.dbname)
        mod_obj = pool.get('ir.model.data') 
        result = mod_obj._get_id(cr, uid, 'crm', 'view_crm_case_phonecalls_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'])
        phonecall_case_obj = pool.get('crm.phonecall')
        opportunity_case_obj = pool.get('crm.opportunity') 
        # Select the view
        
        data_obj = pool.get('ir.model.data')
        id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_phone_tree_view')
        id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_phone_form_view')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id

        opportunites = opportunity_case_obj.browse(cr, uid, data['ids'])
        for opportunity in opportunites:
            #TODO : Take Other Info from opportunity            
            new_case = phonecall_case_obj.create(cr, uid, {
                    'name' : opportunity.name,
                    'case_id' : opportunity.id,
                    'user_id' : form['user_id'],
                    'categ_id' : form['category_id'],
                    'description' : form['note'],
                    'date' : form['deadline'], 
                    'section_id' : form['section_id'],
                    'partner_id': opportunity.partner_id.id,
                    'partner_address_id':opportunity.partner_address_id.id,
                    'description': data['form']['note'] or opportunity.description,
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

    states = {
        'init': {
            'actions': [_default_values],
            'result': {'type': 'form', 'arch': case_form, 'fields': case_fields,
                'state' : [('end', 'Cancel','gtk-cancel'),('order', 'Schedule Phone Call','gtk-go-forward')]}
        },
        'order': {
            'actions': [],
            'result': {'type': 'action', 'action': _doIt, 'state': 'end'}
        }
    }

opportunity2phonecall('crm.opportunity.reschedule_phone_call')

class opportunity2meeting(wizard.interface):

    def _makeMeeting(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        opportunity_case_obj = pool.get('crm.opportunity')
        meeting_case_obj = pool.get('crm.meeting')        
        for opportunity in opportunity_case_obj.browse(cr, uid, data['ids']):
            new_meeting_id = meeting_case_obj.create(cr, uid, {
                'name': opportunity.name,
                'date': opportunity.date,
                'section_id' : opportunity.section_id and opportunity.section_id.id or False,
                'date_deadline': opportunity.date_deadline,
                'description':opportunity.description,
                'opportunity_id':opportunity.id
                })
            new_meeting = meeting_case_obj.browse(cr, uid, new_meeting_id)
            vals = {}
            opportunity_case_obj.write(cr, uid, [opportunity.id], vals)            
            meeting_case_obj.case_open(cr, uid, [new_meeting_id])        
        data_obj = pool.get('ir.model.data')
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
        return {            
            'name': _('Meetings'),
            'domain' : "[('opportunity_id','in',%s)]"%(data['ids']),         
            'view_type': 'form',
            'view_mode': 'calendar,form,tree',
            'res_model': 'crm.meeting',
            'view_id': False,
            'views': [(id1,'calendar'),(id2,'form'),(id3,'tree')],
            'type': 'ir.actions.act_window',
            'search_view_id': id['res_id']
            }

    states = {
        'init': {
            'actions': [],
            'result': {'type': 'action', 'action': _makeMeeting, 'state': 'order'}
        },
        'order': {
            'actions': [],
            'result': {'type': 'state', 'state': 'end'}
        }
    }
opportunity2meeting('crm.opportunity.meeting_set')

class partner_opportunity(wizard.interface):

    case_form = """<?xml version="1.0"?>
                <form string="Create Opportunity">
                    <field name="name"/>
                    <field name="partner_id" readonly="1"/>
                    <newline/>
                    <field name="planned_revenue"/>
                    <field name="probability"/>
                </form>"""

    case_fields = {
        'name' : {'type' :'char', 'size' :64, 'string' :'Opportunity Name', 'required' :True}, 
        'planned_revenue' : {'type' :'float', 'digits' :(16, 2), 'string' : 'Expected Revenue'}, 
        'probability' : {'type' :'float', 'digits' :(16, 2), 'string' : 'Success Probability'}, 
        'partner_id' : {'type' :'many2one', 'relation' :'res.partner', 'string' :'Partner'}, 
    }

    def _select_data(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        part_obj = pool.get('res.partner')
        part = part_obj.read(cr, uid, data['id' ], ['name'])
        return {'partner_id' : data['id'], 'name' : part['name'] }

    def _make_opportunity(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        data_obj = pool.get('ir.model.data')
        result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_opportunities_filter')
        res = data_obj.read(cr, uid, result, ['res_id'])        

        id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_form_view_oppor')
        id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_tree_view_oppor')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id
        
        part_obj = pool.get('res.partner')
        address = part_obj.address_get(cr, uid, data['ids' ])
        
        
        categ_obj = pool.get('crm.case.categ')
        categ_ids = categ_obj.search(cr, uid, [('name','ilike','Part%')])

        case_obj = pool.get('crm.opportunity')
        opp_id = case_obj.create(cr, uid, {            
            'name' : data['form']['name'], 
            'planned_revenue' : data['form']['planned_revenue'], 
            'probability' : data['form']['probability'], 
            'partner_id' : data['form']['partner_id'], 
            'partner_address_id' : address['default'],
            'categ_id' : categ_ids[0],            
            'state' :'draft', 
        })
        value = {            
            'name' : _('Opportunity'), 
            'view_type' : 'form', 
            'view_mode' : 'form,tree', 
            'res_model' : 'crm.opportunity', 
            'res_id' : opp_id, 
            'view_id' : False, 
            'views' : [(id2, 'form'), (id3, 'tree'), (False, 'calendar'), (False, 'graph')], 
            'type' : 'ir.actions.act_window', 
            'search_view_id' : res['res_id'] 
        }
        return value

    states = {
        'init' : {
            'actions' : [_select_data], 
            'result' : {'type' : 'form', 'arch' : case_form, 'fields' : case_fields, 
                'state' : [('end', 'Cancel', 'gtk-cancel'), ('confirm', 'Create Opportunity', 'gtk-go-forward')]}
        }, 
        'confirm' : {
            'actions' : [], 
            'result' : {'type' : 'action', 'action' : _make_opportunity, 'state' : 'end'}
        }
    }

partner_opportunity('crm.case.opportunity.partner_opportunity')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
