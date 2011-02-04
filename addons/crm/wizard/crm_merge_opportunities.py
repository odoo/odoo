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

class crm_merge_opportunity(osv.osv_memory):
    """Merge two Opportunities"""

    _name = 'crm.merge.opportunity'
    _description = 'Merge two Opportunities'

    def action_merge(self, cr, uid, ids, context=None):
        """
        This function merges opportunities
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Phonecall to Opportunity IDs
        @param context: A standard dictionary for contextual values

        @return : Dictionary value for created Opportunity form
        """
        record_id = context and context.get('active_id') or False
        opp_obj = self.pool.get('crm.lead')
        if self.datas:
            obj_opportunity = self.browse(cr, uid, ids[0], context=context)
            if hasattr(obj_opportunity, 'opportunity_ids'):
                op_ids = obj_opportunity.opportunity_ids
        else:
            op_ids = context.get('opportunity_ids')
        
        if len(op_ids) <= 1:
            raise osv.except_osv(_('Warning !'),_('Please select more than one opportunities.'))
        elif op_ids[0].id == record_id:
            op_ids = op_ids[1:]
        
        first_opp = opp_obj.browse(cr, uid, record_id, context=context)
        first_opp_data = {}

        for opp in op_ids:
            first_opp_data = {
                'partner_id': first_opp.partner_id.id or opp.partner_id.id,
                'stage_id': first_opp.stage_id.id or opp.stage_id.id, 
                'section_id': first_opp.section_id.id or opp.section_id.id,
                'categ_id': first_opp.categ_id.id or opp.categ_id.id,
                'type_id': first_opp.type_id.id or opp.type_id.id,
                'channel_id': first_opp.channel_id.id or opp.channel_id.id,
                'user_id': first_opp.user_id.id or opp.user_id.id,
                'country_id': first_opp.country_id.id or opp.country_id.id, 
                'state_id': first_opp.state_id.id or opp.state_id.id,
                'partner_address_id': first_opp.partner_address_id.id or opp.partner_address_id.id,
                'priority': first_opp.priority or opp.priority,
                'title': first_opp.title.id or opp.title.id,
                'function': first_opp.function or opp.function,
                'email_from': first_opp.email_from or opp.email_from,
                'phone': first_opp.phone or opp.phone,
                'description': first_opp.description or opp.description,
                'partner_name': first_opp.partner_name or opp.partner_name,
                'street': first_opp.street or opp.street,
                'street2': first_opp.street2 or opp.street2,
                'zip': first_opp.zip or opp.zip,
                'city': first_opp.city or opp.city,
                'fax': first_opp.fax or opp.fax,
                'mobile': first_opp.mobile or opp.mobile,
                'email_cc': ','.join(filter(lambda x: x, [opp.email_cc, first_opp.email_cc])),
                'type': 'opportunity', 
                'state': 'open'
            }
            for history in opp.message_ids:
                if history.history:
                    new_history = message_obj.copy(cr, uid, history.id, default={'res_id': opp.id})
            opp_obj._history(cr, uid, [first_opp], _('Merged from Opportunity: %s : Information lost : [Partner: %s, Stage: %s, Section: %s, Salesman: %s]') % (opp.name, opp.partner_id.name or '', opp.stage_id.name or '', opp.section_id.name or '', opp.user_id.name or ''))
        
        opp_obj.write(cr, uid, [first_opp.id], first_opp_data)
        
        unlink_ids = map(lambda x: x.id, op_ids)
        opp_obj.unlink(cr, uid, unlink_ids)
        
        models_data = self.pool.get('ir.model.data')

        # Get Opportunity views
        result = models_data._get_id(
            cr, uid, 'crm', 'view_crm_case_opportunities_filter')
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
        
        return {
                'name': _('Opportunity'),
                'view_type': 'form',
                'view_mode': 'tree, form',
                'res_model': 'crm.lead',
                'domain': [('type', '=', 'opportunity')],
                'res_id': int(first_opp.id),
                'view_id': False,
                'views': [(opportunity_view_form, 'form'),
                          (opportunity_view_tree, 'tree'),
                          (False, 'calendar'), (False, 'graph')],
                'type': 'ir.actions.act_window',
        }

    _columns = {
        'opportunity_ids' : fields.many2many('crm.lead',  'merge_opportunity_rel', 'merge_id', 'opportunity_id', 'Opportunities', domain=[('type', '=', 'opportunity')]),
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
        record_ids = context and context.get('active_ids', False) or False
        res = super(crm_merge_opportunity, self).default_get(cr, uid, fields, context=context)

        if record_ids:
            if 'opportunity_ids' in fields:
                res.update({'opportunity_ids': record_ids})

        return res

crm_merge_opportunity()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
