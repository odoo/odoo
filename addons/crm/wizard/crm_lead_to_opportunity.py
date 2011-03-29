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

import time

class crm_lead2opportunity_partner(osv.osv_memory):
    _name = 'crm.lead2opportunity.partner'
    _description = 'Lead To Opportunity Partner'
    _inherit = 'crm.lead2partner'

    _columns = {
        'action': fields.selection([('exist', 'Link to an existing partner'), \
                                    ('create', 'Create a new partner'), \
                                    ('nothing', 'Do not link to a partner')], \
                                    'Action', required=True),
        'name': fields.selection([('convert', 'Convert to Opportunity'), ('merge', 'Merge with existing Opportunity')],'Select Action', required=True),
        'opportunity_ids': fields.many2many('crm.lead',  'merge_opportunity_rel', 'merge_id', 'opportunity_id', 'Opportunities', domain=[('type', '=', 'opportunity')]),
    }

    def default_get(self, cr, uid, fields, context=None):
        """
            Default get for name, opportunity_ids
            if there is an exisitng  partner link to the lead, find all existing opportunity link with this partnet to merge
            all information together
        """
        lead_obj = self.pool.get('crm.lead')


        res = super(crm_lead2opportunity_partner, self).default_get(cr, uid, fields, context=context)
        opportunities = res.get('opportunity_ids') or []

        partner_id = False
        for lead in lead_obj.browse(cr, uid, opportunities, context=context):
            partner_id = lead.partner_id and lead.partner_id.id or False

        if not partner_id and res.get('partner_id'):
            partner_id = res.get('partner_id')

        ids = []
        if partner_id:
            ids = lead_obj.search(cr, uid, [('partner_id', '=', partner_id), ('type', '=', 'opportunity'), '!', ('state', 'in', ['done', 'cancel'])])
            opportunities.append(ids[0])

        if 'action' in fields:
            res.update({'action' : partner_id and 'exist' or 'create'})
        if 'partner_id' in fields:
            res.update({'partner_id' : partner_id})
        if 'name' in fields:
            res.update({'name' : ids and 'merge' or 'convert'})
        if 'opportunity_ids' in fields:
            res.update({'opportunity_ids': opportunities})


        return res

    def view_init(self, cr, uid, fields, context=None):
        """
        This function checks for precondition before wizard executes
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values

        """
        if context is None:
            context = {}
        lead_obj = self.pool.get('crm.lead')

        for lead in lead_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if lead.state in ['done', 'cancel']:
                raise osv.except_osv(_("Warning !"), _("Closed/Cancelled \
Leads Could not convert into Opportunity"))
        return False

    def _convert(self, cr, uid, ids, lead, partner_id, stage_ids, context=None):
        leads = self.pool.get('crm.lead')
        address_id = False
        if partner_id:
            address_id = self.pool.get('res.partner.address').search(cr, uid,
                                                                 [('partner_id', '=', partner_id)],
                                                                 order='create_date desc',
                                                                 limit=1)
        vals = {
            'planned_revenue': lead.planned_revenue,
            'probability': lead.probability,
            'name': lead.name,
            'partner_id': partner_id,
            'user_id': (lead.user_id and lead.user_id.id),
            'type': 'opportunity',
            'stage_id': stage_ids and stage_ids[0] or False,
            'date_action': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        if address_id:
            vals['partner_address_id'] = address_id[0]

        lead.write(vals, context=context)
        leads.history(cr, uid, [lead], _('Converted to opportunity'), details='Converted to Opportunity', context=context)
        if lead.partner_id:
            msg_ids = [ x.id for x in lead.message_ids]
            self.pool.get('mailgate.message').write(cr, uid, msg_ids, {
                        'partner_id': lead.partner_id.id
                    }, context=context)
            leads.log(cr, uid, lead.id, _("Lead '%s' has been converted to an opportunity.") % lead.name)


    def action_apply(self, cr, uid, ids, context=None):
        """
        This converts lead to opportunity and opens Opportunity view
        @param ids: ids of the leads to convert to opportunities

        @return : View dictionary opening the Opportunity form view
        """
        if not context:
            context = {}

        record_id = context and context.get('active_ids') or False
        if not record_id:
            return {'type': 'ir.actions.act_window_close'}

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

        for lead in leads.browse(cr, uid, record_id, context=context):
            if lead.section_id:
                stage_ids = self.pool.get('crm.case.stage').search(cr, uid, [('type','=','opportunity'),('sequence','>=',1), ('section_ids','=', lead.section_id.id)])
            else:
                stage_ids = self.pool.get('crm.case.stage').search(cr, uid, [('type','=','opportunity'),('sequence','>=',1)])

            data = self.browse(cr, uid, ids[0], context=context)


            if data.action == 'create':
                partner_ids = []
                partner_ids = self._create_partner(cr, uid, ids, context=context)
                partner_id = partner_ids and partner_ids[0]
            elif data.action == 'exist':
                partner_id = data.partner_id and data.partner_id.id
            else:
                partner_id = False


            self._convert(cr, uid, ids, lead, partner_id, stage_ids, context=context)
            #If we convert in mass, don't merge if there is no other opportunity but no warning
            if data.name == 'merge' and (len(data.opportunity_ids) > 1 or not context.get('mass_convert') ):
                merge_obj = self.pool.get('crm.merge.opportunity')
                self.write(cr, uid, ids, {'opportunity_ids' : [(6,0, [data.opportunity_ids[0].id])]}, context=context)
                context.update({'lead_ids' : record_id})
                return merge_obj.merge(cr, uid, data.opportunity_ids, context=context)

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

crm_lead2opportunity_partner()

class crm_lead2opportunity_mass_convert(osv.osv_memory):
    _name = 'crm.lead2opportunity.partner.mass'
    _description = 'Mass Lead To Opportunity Partner'
    _inherit = 'crm.lead2opportunity.partner'


    _columns = {
            'user_ids':  fields.many2many('res.users', 'mass_convert_rel', 'user_id', 'wizard_id', 'Salesmans'),
            'section_id': fields.many2one('crm.case.section', 'Sales Team'),

    }

    def mass_convert(self, cr, uid, ids, context=None):
        lead_obj = self.pool.get('crm.lead')
        if not context:
            context = {}

        active_ids = context.get('active_ids')
        data = self.browse(cr, uid, ids, context=context)[0]

        salesteam = data.section_id and data.section_id.id
        if data.user_ids:
            salesmans = map(lambda x : x.id, data.user_ids)
            index = 0
        else:
            salesmans = False

        for lead_id in active_ids:
            value = {}
            if salesteam:
                value['section_id'] = salesteam
            if salesmans:
                value['user_id'] = salesmans[index]
                index += 1
                index = index < len(salesmans) and index or 0
            if value:
                lead_obj.write(cr, uid, [lead_id], value, context=context)

            context['active_ids'] = [lead_id]
            value = self.default_get(cr, uid, ['partner_id', 'opportunity_ids'], context=context)
            value['opportunity_ids'] = [(6, 0, value['opportunity_ids'])]
            self.write(cr, uid, ids, value, context=context)

            self.action_apply(cr, uid, ids, context=context)



        models_data = self.pool.get('ir.model.data')
        result = models_data._get_id(cr, uid, 'crm', 'view_crm_case_opportunities_filter')
        opportunity_view_search = models_data.browse(cr, uid, result, context=context).res_id

        return {
            'name': _('Opportunity'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'crm.lead',
            'domain': [('type', '=', 'opportunity'), ('id', 'in', active_ids)],
            'type': 'ir.actions.act_window',
            'search_view_id': opportunity_view_search,
        }

crm_lead2opportunity_mass_convert()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
