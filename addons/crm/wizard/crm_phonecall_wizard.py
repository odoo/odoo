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

import wizard
import netsvc
import ir
import pooler
from tools.translate import _

class partner_create(wizard.interface):

    case_form = """<?xml version="1.0"?>
    <form string="Create a Partner">
        <label string="Are you sure you want to create a partner based on this phonecall ?" colspan="4"/>
        <label string="You may have to verify that this partner does not exist already." colspan="4"/>
        <!--field name="close"/-->
    </form>"""

    case_fields = {
        'close': {'type':'boolean', 'string':'Close Phonecall'}
    }

    partner_form = """<?xml version="1.0"?>
    <form string="Create a Partner">
        <label string="Are you sure you want to create a partner based on this lead ?" colspan="4"/>
        <label string="You may have to verify that this partner does not exist already." colspan="4"/>
        <newline />
        <field name="action"/>
        <group attrs="{'invisible':[('action','!=','exist')]}">
            <field name="partner_id"/>
        </group>
    </form>"""

    partner_fields = {
        'action': {'type':'selection',
                'selection':[('exist','Link to an existing partner'),('create','Create a new partner')],
                'string':'Action', 'required':True, 'default': lambda *a:'exist'},
        'partner_id' : {'type':'many2one', 'relation':'res.partner', 'string':'Partner'},
    }

    def _selectPartner(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        case_obj = pool.get('crm.phonecall')
        for case in case_obj.browse(cr, uid, data['ids']):
            if case.partner_id:
                raise wizard.except_wizard(_('Warning !'),
                    _('A partner is already defined on this phonecall.'))                        
        return {}

    def _create_partner(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)        
        case_obj = pool.get('crm.phonecall')
        partner_obj = pool.get('res.partner')
        contact_obj = pool.get('res.partner.address')
        partner_ids = []
        partner_id = False
        contact_id = False
        for case in case_obj.browse(cr, uid, data['ids']):
            if data['form']['action'] == 'create':
                partner_id = partner_obj.create(cr, uid, {
                    'name': case.partner_name or case.name,
                    'user_id': case.user_id.id,
                    'comment': case.description,
                })
                contact_id = contact_obj.create(cr, uid, {
                    'partner_id': partner_id,
                    'name': case.name,
                    'phone': case.phone,
                    'mobile': case.mobile,
                    'email': case.email_from
                })

            else:
                if data['form']['partner_id']:
                    partner = partner_obj.browse(cr,uid,data['form']['partner_id'])
                    partner_id = partner.id
                    contact_id = partner.address and partner.address[0].id

            partner_ids.append(partner_id)
            vals = {}
            if partner_id:
                vals.update({'partner_id': partner_id})
            if contact_id:
                vals.update({'partner_address_id': contact_id})
            case_obj.write(cr, uid, [case.id], vals)   
        return partner_ids

    def _make_partner(self, cr, uid, data, context): 
        pool = pooler.get_pool(cr.dbname)             
        partner_ids = self._create_partner(cr, uid, data, context)
        mod_obj = pool.get('ir.model.data') 
        result = mod_obj._get_id(cr, uid, 'base', 'view_res_partner_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'])
        value = {
            'domain': "[]",
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'res.partner',
            'res_id': partner_ids and int(partner_ids[0]) or False,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'search_view_id': res['res_id'] 
        }
        return value

    states = {
        'init': {
            'actions': [_selectPartner],
            'result': {'type': 'form', 'arch': case_form, 'fields': case_fields,
                'state' : [('end', 'Cancel', 'gtk-cancel'),('create_partner', 'Create Partner', 'gtk-go-forward')]}
        },
        'create_partner': {
            'actions': [],
            'result': {'type': 'form', 'arch': partner_form, 'fields': partner_fields,
                'state' : [('end', 'Cancel', 'gtk-cancel'),('create', 'Continue', 'gtk-go-forward')]}
        },
        'create': {
            'actions': [],
            'result': {'type': 'action', 'action': _make_partner, 'state': 'end'}
        }
    }


partner_create('crm.phonecall.partner_create')

class phonecall2opportunity(partner_create):
    
    case_form = """<?xml version="1.0"?>
    <form string="Convert To Opportunity">
        <field name="name"/>
        <field name="partner_id"/>
        <newline/>
        <field name="planned_revenue"/>
        <field name="probability"/>
    </form>"""

    case_fields = {
        'name': {'type':'char', 'size':64, 'string':'Opportunity Summary', 'required':True},
        'planned_revenue': {'type':'float', 'digits':(16,2), 'string': 'Expected Revenue'},
        'probability': {'type':'float', 'digits':(16,2), 'string': 'Success Probability'},
        'partner_id' : {'type':'many2one', 'relation':'res.partner', 'string':'Partner'},
    }
    
    def _check_state(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        case_obj = pool.get('crm.phonecall')
        for case in case_obj.browse(cr, uid, data['ids']):
            if case.state in ['done', 'cancel']:
                raise wizard.except_wizard(_('Warning !'),
                    _('Closed/Cancelled Phone Call Could not convert into Opportunity.'))
        return {}

    def _selectopportunity(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        case_obj = pool.get('crm.phonecall')
        case = case_obj.browse(cr, uid, data['id'])
        return {'name': case.name, 'partner_id':case.partner_id and case.partner_id.id or False}

    def _selectChoice(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        case_obj = pool.get('crm.phonecall')
        for case in case_obj.browse(cr, uid, data['ids']):
            if not case.partner_id:
                return 'create_partner'
        return 'opportunity'

    def _makeOrder(self, cr, uid, data, context):
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

        phonecall_case_obj = pool.get('crm.phonecall')
        opportunity_case_obj = pool.get('crm.opportunity')
        for phonecall in phonecall_case_obj.browse(cr, uid, data['ids']):                     
            new_opportunity_id = opportunity_case_obj.create(cr, uid, {            
                'name': data['form']['name'],
                'planned_revenue': data['form']['planned_revenue'],
                'probability': data['form']['probability'],
                'partner_id': data['form']['partner_id'],                 
                'section_id': phonecall.section_id.id,
                'description': phonecall.description,         
                'phonecall_id': phonecall.id,
                'priority': phonecall.priority,
                'phone': phonecall.partner_phone,
            })
            new_opportunity = opportunity_case_obj.browse(cr, uid, new_opportunity_id)
            vals = {
                'partner_id': data['form']['partner_id'], 
                'opportunity_id' : new_opportunity_id,                
                }            
            phonecall_case_obj.write(cr, uid, [phonecall.id], vals)
            phonecall_case_obj.case_close(cr, uid, [phonecall.id])
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

    def _makePartner(self, cr, uid, data, context):
        partner_ids = self._create_partner(cr, uid, data, context)
        return {}

    states = {
        'init': {
            'actions': [_check_state],
            'result': {'type':'choice','next_state':_selectChoice}
        },
        'create_partner': {
            'actions': [],
            'result': {'type': 'form', 'arch': partner_create.partner_form, 'fields': partner_create.partner_fields,
                'state' : [('end', 'Cancel', 'gtk-cancel'),('opportunity', 'Skip', 'gtk-goto-last'),('create', 'Continue', 'gtk-go-forward')]}
        },
        'create': {
            'actions': [],
            'result': {'type': 'action', 'action': _makePartner, 'state':'opportunity' }
        },
        'opportunity': {
            'actions': [_selectopportunity],
            'result': {'type': 'form', 'arch': case_form, 'fields': case_fields,
                'state' : [('end', 'Cancel', 'gtk-cancel'),('confirm', 'Create Opportunity', 'gtk-go-forward')]}
        },
        'confirm': {
            'actions': [],
            'result': {'type': 'action', 'action': _makeOrder, 'state': 'end'}
        }
    }

phonecall2opportunity('crm.phonecall.opportunity_set')

class phonecall2meeting(wizard.interface):

    def _makeMeeting(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        phonecall_case_obj = pool.get('crm.phonecall')                   
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
            'domain' : "[('phonecall_id','in',%s)]"%(data['ids']),         
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
phonecall2meeting('crm.phonecall.meeting_set')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
