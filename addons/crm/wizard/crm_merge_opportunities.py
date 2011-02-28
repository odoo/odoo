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

    def _get_first_not_null_id(self, attr, ops):
        for op in ops:
            if hasattr(op, attr) and getattr(op, attr):
                return getattr(op, attr).id
        return False

    def _get_first_not_null(self, attr, ops):
        for op in ops:
            if hasattr(op, attr) and getattr(op, attr):
                return getattr(op, attr)
        return False

    def _concat_all(self, attr, ops):
        return ', '.join([getattr(op, attr) for op in ops if hasattr(op, attr) and getattr(op, attr)])


    def get_attachments(self, cr, uid, id, context=None):
        attach_obj = self.pool.get('ir.attachment')
        result = []
        attach_ids = attach_obj.search(cr, uid, [('res_model' , '=', 'crm.lead'), ('res_id', '=', id)])
        return attach_ids

    def set_attachements_res_id(self, cr, uid, op_id, attach_ids, context=None):
        attach_obj = self.pool.get('ir.attachment')
        attach_obj.write(cr, uid, attach_ids, {'res_id' : op_id})



    def merge(self, cr, uid, op_ids, context=None):
        """
            @param opp_ids : list of opportunities ids to merge
        """
        opp_obj = self.pool.get('crm.lead')
        message_obj = self.pool.get('mailgate.message')

        lead_ids = context and context.pop('lead_ids', []) or []


        if len(op_ids) <= 1:
            raise osv.except_osv(_('Warning !'),_('Please select more than one opportunities.'))

        opportunities = opp_obj.browse(cr, uid, lead_ids, context=context)
        opportunities_list = list(set(op_ids) - set(opportunities))

        if opportunities :
            first_opportunity = opportunities[0]
            tail_opportunities = opportunities_list
        else:
            first_opportunity = opportunities_list[0]
            tail_opportunities = opportunities_list[1:]


        data = {
                'partner_id': self._get_first_not_null_id('partner_id', op_ids),  # !!
                'title': self._get_first_not_null_id('title', op_ids),
                'name' : self._concat_all('name', op_ids),  #not lost
                'categ_id' : self._get_first_not_null_id('categ_id', op_ids), # !!
                'channel_id' : self._get_first_not_null_id('channel_id', op_ids), # !!
                'city' : self._get_first_not_null('city', op_ids),  # !!
                'company_id' : self._get_first_not_null_id('company_id', op_ids), #!!
                'contact_name' : self._concat_all('contact_name', op_ids), #not lost
                'country_id' : self._get_first_not_null_id('country_id', op_ids), #!!
                'partner_address_id' : self._get_first_not_null_id('partner_address_id', op_ids), #!!
                'partner_assigned_id' : hasattr(opp_obj,'partner_assigned_id') and self._get_first_not_null_id('partner_assigned_id', op_ids), #!!
                'type_id' : self._get_first_not_null_id('type_id', op_ids), #!!
                'user_id' : self._get_first_not_null_id('user_id', op_ids), #!!
                'section_id' : self._get_first_not_null_id('section_id', op_ids), #!!
                'state_id' : self._get_first_not_null_id('state_id', op_ids),
                'description' : self._concat_all('description', op_ids),  #not lost
                'email' : self._get_first_not_null('email', op_ids), # !!
                'fax' : self._get_first_not_null('fax', op_ids),
                'mobile' : self._get_first_not_null('mobile', op_ids),
                'partner_latitude' : hasattr(opp_obj,'partner_latitude') and self._get_first_not_null('partner_latitude', op_ids),
                'partner_longitude' : hasattr(opp_obj,'partner_longitude') and self._get_first_not_null('partner_longitude', op_ids),
                'partner_name' : self._get_first_not_null('partner_name', op_ids),
                'phone' : self._get_first_not_null('phone', op_ids),
                'probability' : self._get_first_not_null('probability', op_ids),
                'planned_revenue' : self._get_first_not_null('planned_revenue', op_ids),
                'street' : self._get_first_not_null('street', op_ids),
                'street2' : self._get_first_not_null('street2', op_ids),
                'zip' : self._get_first_not_null('zip', op_ids),
                'state' : 'open'

            }

        #copy message into the first opportunity + merge attachement
        for opp in tail_opportunities:
            attach_ids = self.get_attachments(cr, uid, opp, context=context)
            self.set_attachements_res_id(cr, uid, first_opportunity.id, attach_ids)
            for history in opp.message_ids:
                new_history = message_obj.copy(cr, uid, history.id, default={'res_id': opp.id})

        #Notification about loss of information
        details = []
        subject = ['Merged opportunities :']
        for opp in op_ids:
            subject.append(opp.name)
            details.append(_('Merged Opportunity: %s\n  Partner: %s\n  Stage: %s\n  Section: %s\n   Salesman: %s\n   Category: %s\n   Channel: %s\n   Company: %s\n   Contact name: %s\n   Email: %s\n   Phone number: %s\n   Fax: %s\n   Mobile: %s\n   State: %s\n   Description: %s\n   Probability: %s\n   Planned revennue: %s\n   Country: %s\n   City: %s\n   Street: %s\n   Street 2: %s\n   Zip 2: %s')  % ( opp.name, opp.partner_id.name or '',
                        opp.stage_id.name or '',
                        opp.section_id.name or '',
                        opp.user_id.name or '',
                        opp.categ_id.name or '',
                        opp.channel_id.name or '',
                        opp.company_id.name or '',
                        opp.contact_name or '',
                        opp.email_from or '',
                        opp.phone or '',
                        opp.fax or '',
                        opp.mobile or '',
                        opp.state_id.name or '',
                        opp.description or '',
                        opp.probability or '',
                        opp.planned_revenue or '',
                        opp.country_id.name or '',
                        opp.city or '',
                        opp.street or '',
                        opp.street2 or '',
                        opp.zip or '',
                        ))
        subject = subject[0] + ", ".join(subject[1:])
        details = "\n\n".join(details)

        opp_obj._history(cr, uid, [first_opportunity], subject, details=details)
        #data.update({'message_ids' : [(6, 0 ,self._concat_o2m('message_ids', op_ids))]})
        opp_obj.write(cr, uid, [first_opportunity.id], data)
        unlink_ids = map(lambda x: x.id, tail_opportunities)
        opp_obj.unlink(cr, uid, unlink_ids, context=context)

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
                'res_id': int(first_opportunity.id),
                'view_id': False,
                'views': [(opportunity_view_form, 'form'),
                          (opportunity_view_tree, 'tree'),
                          (False, 'calendar'), (False, 'graph')],
                'type': 'ir.actions.act_window',
        }


    def action_merge(self, cr, uid, ids, context=None):
        obj_opportunity = self.browse(cr, uid, ids[0], context=context)
        op_ids = obj_opportunity.opportunity_ids
        self.write(cr, uid, ids, {'opportunity_ids' : [(6,0, [op_ids[0].id])]}, context=context)
        return self.merge(cr, uid, op_ids, context)


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
