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
        result = ''
        for op in ops:
            if hasattr(op, attr) and getattr(op, attr):
                result += ' # ' + getattr(op, attr)
        return result

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
        message_obj = self.pool.get('mailgate.message')
        if self.datas:
            obj_opportunity = self.browse(cr, uid, ids[0], context=context)
            if hasattr(obj_opportunity, 'opportunity_ids'):
                op_ids = obj_opportunity.opportunity_ids
        else:
            op_ids = context.get('opportunity_ids')
        
        if len(op_ids) <= 1:
            raise osv.except_osv(_('Warning !'),_('Please select more than one opportunities.'))
       
        first_opp = op_ids[0]
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
                
            }
        
        
        
        #copy message into the first opportunity
        for opp in op_ids[1:]:
            for history in opp.message_ids:
                new_history = message_obj.copy(cr, uid, history.id, default={'res_id': opp.id})
        #Notification about loss of information
        for opp in op_ids:
            opp_obj._history(cr, uid, [first_opp], _('Merged from Opportunity: %s : Information lost : [Partner: %s, Stage: %s, Section: %s, Salesman: %s, Category: %s, Channel: %s, City: %s, Company: %s, Country: %s, Email: %s, Phone number: %s, Contact name: %s]')  
                    % ( opp.name, opp.partner_id.name or '', 
                        opp.stage_id.name or '', 
                        opp.section_id.name or '', 
                        opp.user_id.name or '',
                        opp.categ_id.name or '', 
                        opp.channel_id.name or '', 
                        opp.city or '', 
                        opp.company_id.name or '',
                        opp.country_id.name or '', 
                        opp.email or '', 
                        opp.phone or '',
                        opp.contact_name or ''))
                    
        #data.update({'message_ids' : [(6, 0 ,self._concat_o2m('message_ids', op_ids))]})
        opp_obj.write(cr, uid, [first_opp.id], data)
        
        unlink_ids = map(lambda x: x.id, op_ids[1:])
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
