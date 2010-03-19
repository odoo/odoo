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
from tools.translate import _
import ir
import netsvc
import pooler
import wizard

#===============================================================================
# Put original wizard because of type=choice in init
# Remove it after solution for type=choice
#===============================================================================

class partner_create(wizard.interface):

    case_form = """<?xml version="1.0"?>
    <form string="Create a Partner">
        <label string="Are you sure you want to create a partner based on this lead ?" colspan="4"/>
        <label string="You may have to verify that this partner does not exist already." colspan="4"/>
        <!--field name="close"/-->
    </form>"""

    case_fields = {
        'close': {'type':'boolean', 'string':'Close Lead'}
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
        case_obj = pool.get('crm.lead')
        partner_obj = pool.get('res.partner')
        contact_obj = pool.get('res.partner.address')
        for case in case_obj.browse(cr, uid, data['ids']):
            if case.partner_id:
                raise wizard.except_wizard(_('Warning !'),
                    _('A partner is already defined on this lead.'))
           
            partner_ids = partner_obj.search(cr, uid, [('name', '=', case.partner_name or case.name)])            
            if not partner_ids and case.email_from:
                address_ids = contact_obj.search(cr, uid, [('email', '=', case.email_from)])
                if address_ids:
                    addresses = contact_obj.browse(cr, uid, address_ids)
                    partner_ids = addresses and [addresses[0].partner_id.id] or False

            partner_id = partner_ids and partner_ids[0] or False
        vals = {'partner_id': partner_id}
        if not partner_id:
            vals['action'] = 'create'            
        return vals

    def _create_partner(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)        
        case_obj = pool.get('crm.lead')
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
                    'email': case.email_from,
                    'fax': case.fax,
                    'title': case.title,
                    'function': case.function and case.function.id or False,
                    'street': case.street,
                    'street2': case.street2,
                    'zip': case.zip,
                    'city': case.city,
                    'country_id': case.country_id and case.country_id.id or False,
                    'state_id': case.state_id and case.state_id.id or False,
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

partner_create('crm.lead.partner_create')


class lead2opportunity(partner_create):

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
        case_obj = pool.get('crm.lead')
        for case in case_obj.browse(cr, uid, data['ids']):
            if case.state != 'open':
                raise wizard.except_wizard(_('Warning !'),
                    _('Lead should be in \'Open\' state before converting to Opportunity.'))
        return {}

    def _selectopportunity(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        case_obj = pool.get('crm.lead')
        case = case_obj.browse(cr, uid, data['id'])
        return {'name': case.name, 'partner_id':case.partner_id and case.partner_id.id or False}

    def _selectChoice(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        case_obj = pool.get('crm.lead')
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

        lead_case_obj = pool.get('crm.lead')
        opportunity_case_obj = pool.get('crm.opportunity')        
        for lead in lead_case_obj.browse(cr, uid, data['ids']):
            new_opportunity_id = opportunity_case_obj.create(cr, uid, {            
                'name': data['form']['name'],
                'planned_revenue': data['form']['planned_revenue'],
                'probability': data['form']['probability'],
                'partner_id': data['form']['partner_id'],
                'section_id':lead.section_id.id,
                'description':lead.description,
                'date_deadline': lead.date_deadline,
                'partner_address_id':lead.partner_address_id.id, 
                'priority': lead.priority,
                'phone': lead.phone,                
                'email_from': lead.email_from
            })       
            
            new_opportunity = opportunity_case_obj.browse(cr, uid, new_opportunity_id)
            
            vals = {
                'partner_id': data['form']['partner_id'],                
                }
            if not lead.opportunity_id:
                vals.update({'opportunity_id' : new_opportunity.id})

            lead_case_obj.write(cr, uid, [lead.id], vals)
            lead_case_obj.case_close(cr, uid, [lead.id])
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
            'actions': [partner_create._selectPartner],
            'result': {'type': 'form', 'arch': partner_create.partner_form, 'fields': partner_create.partner_fields,
                'state' : [('end', 'Cancel', 'gtk-cancel'),('opportunity', 'Skip', 'gtk-goto-last'), ('create', 'Continue', 'gtk-go-forward')]}
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

lead2opportunity('crm.lead.opportunity_set')

class crm_lead2opportunity(osv.osv_memory):
    _name = 'crm.lead2opportunity'
    _description = 'Lead To Opportunity'

    def action_cancel(self, cr, uid, ids, context=None):
        """
        Closes Lead To Opportunity form
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Lead to Partner's IDs
        @param context: A standard dictionary for contextual values

        """
        return {'type': 'ir.actions.act_window_close'}

    def action_apply(self, cr, uid, ids, context=None):
        """
        This converts lead to opportunity and opens Opportunity view
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Lead to Opportunity IDs
        @param context: A standard dictionary for contextual values

        @return : Dictionary value for created Opportunity form
        """
        value = {}
        record_id = context and context.get('active_id', False) or False
        if record_id:
            lead_obj = self.pool.get('crm.lead')
            opp_obj = self. pool.get('crm.opportunity')
            data_obj = self.pool.get('ir.model.data')

            # Get Opportunity views
            result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_opportunities_filter')
            res = data_obj.read(cr, uid, result, ['res_id'])
            id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_form_view_oppor')
            id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_tree_view_oppor')
            if id2:
                id2 = data_obj.browse(cr, uid, id2, context=context).res_id
            if id3:
                id3 = data_obj.browse(cr, uid, id3, context=context).res_id

            lead = lead_obj.browse(cr, uid, record_id, context=context)

            for this in self.browse(cr, uid, ids, context=context):
                new_opportunity_id = opp_obj.create(cr, uid, {
                        'name': this.name,
                        'planned_revenue': this.planned_revenue,
                        'probability': this.probability,
                        'partner_id': lead.partner_id and lead.partner_id.id or False ,
                        'section_id': lead.section_id and lead.section_id.id or False,
                        'description': lead.description or False,
                        'date_deadline': lead.date_deadline or False,
                        'partner_address_id': lead.partner_address_id and \
                                        lead.partner_address_id.id or False ,
                        'priority': lead.priority,
                        'phone': lead.phone,
                        'email_from': lead.email_from
                    })

                new_opportunity = opp_obj.browse(cr, uid, new_opportunity_id)
                vals = {
                        'partner_id': this.partner_id and this.partner_id.id or False,
                        }
                if not lead.opportunity_id:
                        vals.update({'opportunity_id' : new_opportunity.id})

                lead_obj.write(cr, uid, [lead.id], vals)
                lead_obj.case_close(cr, uid, [lead.id])
                opp_obj.case_open(cr, uid, [new_opportunity_id])

            value = {
                    'name': _('Opportunity'),
                    'view_type': 'form',
                    'view_mode': 'form,tree',
                    'res_model': 'crm.opportunity',
                    'res_id': int(new_opportunity_id),
                    'view_id': False,
                    'views': [(id2, 'form'), (id3, 'tree'), (False, 'calendar'), (False, 'graph')],
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

    def view_init(self, cr, uid, fields, context=None):
        """
        This function checks for precondition before wizard executes
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values

        """
        lead_obj = self.pool.get('crm.lead')

        for lead in lead_obj.browse(cr, uid, context.get('active_ids', [])):
            if lead.state in ['done', 'cancel']:
                raise osv.except_osv(_("Warning !"), _("Closed/Cancelled \
Leads Could not convert into Opportunity"))
            if lead.state != 'open':
                raise osv.except_osv(_('Warning !'), _('Lead should be in \
\'Open\' state before converting to Opportunity.'))
        return True

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values

        @return : default values of fields.
        """
        lead_obj = self.pool.get('crm.lead')
        data = context and context.get('active_ids', []) or []
        res = super(crm_lead2opportunity, self).default_get(cr, uid, fields, context=context)

        for lead in lead_obj.browse(cr, uid, data, []):
            if 'name' in fields:
                res.update({'name': lead.partner_name})
            if 'partner_id' in fields:
                res.update({'partner_id': lead.partner_id and lead.partner_id.id or False})
        return res

crm_lead2opportunity()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
