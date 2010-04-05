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
            history_obj = self.pool.get('crm.case.history')
            model_obj = self.pool.get('ir.model')

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
            model_ids = model_obj.search(cr, uid, [('model', '=', 'crm.opportunity')])


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
                
                # Copy lead history to opportunity
                for his_id in lead.history_line:
                    history_ids = history_obj.copy(cr, uid, his_id.id, \
                                                {'model_id': model_ids[0], \
                                                'res_id': new_opportunity_id})

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
        return False

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
        rec_ids = context and context.get('active_ids', [])
        partner_id = context.get('partner_id', False)
        data = context and context.get('active_ids', []) or []
        res = super(crm_lead2opportunity, self).default_get(cr, uid, fields, context=context)
        for lead in lead_obj.browse(cr, uid, data, context=context):
            if 'name' in fields:
                res.update({'name': lead.partner_name})
            if 'partner_id' in fields:
                res.update({'partner_id': partner_id and partner_id[0] or False})
        return res

crm_lead2opportunity()


class crm_lead2opportunity_partner(osv.osv_memory):
    _name = 'crm.lead2opportunity.partner'
    _description = 'Lead To Opportunity Partner'
    _inherit = 'crm.lead2partner'

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner'), 
        'action': fields.selection([('exist', 'Link to an existing partner'), ('create', 'Create a new partner')], 'Action'), 
    }
    
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
        partner_obj = self.pool.get('res.partner')
        contact_obj = self.pool.get('res.partner.address')
        rec_ids = context and context.get('active_ids', [])
        partner_id = False

        data = context and context.get('active_ids', []) or []
        res = super(crm_lead2opportunity_partner, self).default_get(cr, uid, fields, context=context)

        for lead in lead_obj.browse(cr, uid, data, context=context):
            partner_ids = partner_obj.search(cr, uid, [('name', '=', lead.partner_name or lead.name)])
            if not partner_ids and lead.email_from:
                address_ids = contact_obj.search(cr, uid, [('email', '=', lead.email_from)])
                if address_ids:
                    addresses = contact_obj.browse(cr, uid, address_ids)
                    partner_ids = addresses and [addresses[0].partner_id.id] or False
            partner_id = partner_ids and partner_ids[0] or False

            if 'partner_id' in fields:
                res.update({'partner_id': partner_id})
            if 'action' in fields:
                res.update({'action': partner_id and 'exist' or 'create'})
        return res
    
    def make_partner(self, cr, uid, ids, context=None):
        """
        This function Makes partner based on action.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Lead to Partner's IDs
        @param context: A standard dictionary for contextual values

        @return : Dictionary value for created Partner form.
        """
        if not context:
            context = {}
        
        partner_ids = self._create_partner(cr, uid, ids, context)
        mod_obj = self.pool.get('ir.model.data')
        result = mod_obj._get_id(cr, uid, 'base', 'view_res_partner_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'])
        value = {}
        data_obj = self.pool.get('ir.model.data')
        data_id = data_obj._get_id(cr, uid, 'crm', 'view_crm_lead2opportunity_create')
        view_id = False
        if data_id:
            view_id = data_obj.browse(cr, uid, data_id, context=context).res_id
        
        context.update({'partner_id': partner_ids})
        value = {            
            'name': _('Create Opportunity'), 
            'view_type': 'form', 
            'view_mode': 'form,tree', 
            'res_model': 'crm.lead2opportunity', 
            'view_id': False, 
            'context': context, 
            'views': [(view_id, 'form')], 
            'type': 'ir.actions.act_window', 
            'target': 'new', 
        }
        return value

    def action_skip(self, cr, uid, ids, context=None):
        """
        This skips partner creation
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Lead to Opportunity IDs
        @param context: A standard dictionary for contextual values

        @return : Dictionary value for Opportunity form
        """
        value = {}
        data_obj = self.pool.get('ir.model.data')
        data_id = data_obj._get_id(cr, uid, 'crm', 'view_crm_lead2opportunity_create')
        view_id = False
        if data_id:
            view_id = data_obj.browse(cr, uid, data_id, context=context).res_id
        
        context.update({'partner_id': False})
        value = {            
            'name': _('Create Opportunity'), 
            'view_type': 'form', 
            'view_mode': 'form,tree', 
            'res_model': 'crm.lead2opportunity', 
            'view_id': False, 
            'context': context, 
            'views': [(view_id, 'form')], 
            'type': 'ir.actions.act_window', 
            'target': 'new', 
        }
        return value
    

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
        return False

crm_lead2opportunity_partner()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
