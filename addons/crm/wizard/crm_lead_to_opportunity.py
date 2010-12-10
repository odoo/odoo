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
        @param ids: ids of the leads to convert to opportunities

        @return : View dictionary opening the Opportunity form view
        """
        record_id = context and context.get('active_id') or False
        if not record_id:
            return {}

        leads = self.pool.get('crm.lead')
        models_data = self.pool.get('ir.model.data')

        # Get Opportunity views
        result = models_data._get_id(
            cr, uid, 'crm', 'view_crm_case_opportunities_filter')
        opportunity_view_search = models_data.browse(
            cr, uid, result, context=context).res_id
        opportunity_view_form = models_data._get_id(
            cr, uid, 'crm', 'crm_case_form_view_oppor')
        opportunity_view_tree = models_data._get_id(
            cr, uid, 'crm', 'crm_case_tree_view_oppor')
        if opportunity_view_form:
            opportunity_view_form = models_data.browse(
                cr, uid, opportunity_view_form, context=context).res_id
        if opportunity_view_tree:
            opportunity_view_tree = models_data.browse(
                cr, uid, opportunity_view_tree, context=context).res_id

        lead = leads.browse(cr, uid, record_id, context=context)
        stage_ids = self.pool.get('crm.case.stage').search(cr, uid, [('type','=','opportunity'),('sequence','>=',1)])

        for this in self.browse(cr, uid, ids, context=context):
            vals ={
                'planned_revenue': this.planned_revenue,
                'probability': this.probability,
                'name': this.name,
                'partner_id': this.partner_id.id,
                'user_id': (this.partner_id.user_id and this.partner_id.user_id.id) or (lead.user_id and lead.user_id.id),
                'type': 'opportunity',
                'stage_id': stage_ids and stage_ids[0] or False
            }
            lead.write(vals, context=context)
            leads.history(cr, uid, [lead], _('Opportunity'), details='Converted to Opportunity', context=context)
            if lead.partner_id:
                msg_ids = [ x.id for x in lead.message_ids]
                self.pool.get('mailgate.message').write(cr, uid, msg_ids, {
                    'partner_id': lead.partner_id.id
                }, context=context)
            self.log(cr, uid, lead.id,
                _("Lead '%s' has been converted to an opportunity.") % lead.name)

        return {
            'name': _('Opportunity'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'crm.lead',
            'domain': [('type', '=', 'opportunity')],
            'res_id': int(lead.id),
            'view_id': False,
            'views': [(opportunity_view_form, 'form'),
                      (opportunity_view_tree, 'tree'),
                      (False, 'calendar'), (False, 'graph')],
            'type': 'ir.actions.act_window',
            'search_view_id': opportunity_view_search
        }

    _columns = {
        'name' : fields.char('Opportunity', size=64, required=True, select=1),
        'probability': fields.float('Success Rate (%)'),
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
        data = context and context.get('active_ids', []) or []
        res = super(crm_lead2opportunity, self).default_get(cr, uid, fields, context=context)
        for lead in lead_obj.browse(cr, uid, data, context=context):
            if 'name' in fields:
                res.update({'name': lead.name})
            if 'partner_id' in fields:
                res.update({'partner_id': lead.partner_id.id or False})
        return res

crm_lead2opportunity()


class crm_lead2opportunity_partner(osv.osv_memory):
    _name = 'crm.lead2opportunity.partner'
    _description = 'Lead To Opportunity Partner'
    _inherit = 'crm.lead2partner'

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'action': fields.selection([('exist', 'Link to an existing partner'), ('create', 'Create a new partner'), ('no','Do not create a partner')], 'Action'),
    }

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
        value = {}
        data_obj = self.pool.get('ir.model.data')
        data_id = data_obj._get_id(cr, uid, 'crm', 'view_crm_lead2opportunity_action')
        view_id = False
        if data_id:
            view_id = data_obj.browse(cr, uid, data_id, context=context).res_id

        context.update({'partner_id': partner_ids})
        value = {
            'name': _('Create Opportunity'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'crm.lead2opportunity.action',
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
        return False

crm_lead2opportunity_partner()

class crm_lead2opportunity_action(osv.osv_memory):
    '''
    Merge with Existing Opportunity or Convert to Opportunity
    '''
    _name = 'crm.lead2opportunity.action'
    _description = 'Convert/Merge Opportunity'
    _columns = {
        'name': fields.selection([('convert', 'Convert to Opportunity'), ('merge', 'Merge with existing Opportunity')],'Select Action', required=True),
    }
    _defaults = {
        'name': 'convert',
    }
    def do_action(self, cr, uid, ids, context=None):
        """
        This function opens form according to selected Action
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Lead to Opportunity IDs
        @param context: A standard dictionary for contextual values
        @return : Dictionary value for Opportunity form
        """
        value = {}
        data_obj = self.pool.get('ir.model.data')
        view_id = False
        for this in self.browse(cr, uid, ids, context=context):
            if this.name == 'convert':
                data_id = data_obj._get_id(cr, uid, 'crm', 'view_crm_lead2opportunity_create')
                if data_id:
                    view_id = data_obj.browse(cr, uid, data_id, context=context).res_id
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
            elif this.name == 'merge':
                data_id = data_obj._get_id(cr, uid, 'crm', 'merge_opportunity_form')
                if data_id:
                    view_id = data_obj.browse(cr, uid, data_id, context=context).res_id
                value = {
                        'name': _('Merge with Existing Opportunity'),
                        'view_type': 'form',
                        'view_mode': 'form,tree',
                        'res_model': 'crm.merge.opportunity',
                        'view_id': False,
                        'context': context,
                        'views': [(view_id, 'form')],
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                    }
        return value

crm_lead2opportunity_action()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
