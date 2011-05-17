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

class crm_phonecall2opportunity(osv.osv_memory):
    """ Converts Phonecall to Opportunity"""

    _name = 'crm.phonecall2opportunity'
    _description = 'Phonecall To Opportunity'

    def action_cancel(self, cr, uid, ids, context=None):
        """
        Closes Phonecall to Opportunity form
        """

        return {'type':'ir.actions.act_window_close'}


    def action_apply(self, cr, uid, ids, context=None):
        """
        This converts Phonecall to Opportunity and opens Phonecall view
        """
        record_id = context and context.get('active_id', False) or False
        if record_id:
            opp_obj = self.pool.get('crm.lead')
            phonecall_obj = self.pool.get('crm.phonecall')
            case = phonecall_obj.browse(cr, uid, record_id, context=context)
            data_obj = self.pool.get('ir.model.data')
            result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_opportunities_filter')
            res = data_obj.read(cr, uid, result, ['res_id'])
            id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_form_view_oppor')
            id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_tree_view_oppor')
            if id2:
                id2 = data_obj.browse(cr, uid, id2, context=context).res_id
            if id3:
                id3 = data_obj.browse(cr, uid, id3, context=context).res_id

            for this in self.browse(cr, uid, ids, context=context):
                address = None
                if this.partner_id:
                    address_id = self.pool.get('res.partner').address_get(cr, uid, [this.partner_id.id])
                    if address_id['default']:
                        address = self.pool.get('res.partner.address').browse(cr, uid, address_id['default'], context=context)
                new_opportunity_id = opp_obj.create(cr, uid, {
                                'name': this.name,
                                'planned_revenue': this.planned_revenue,
                                'probability': this.probability,
                                'partner_id': this.partner_id and this.partner_id.id or False,
                                'partner_address_id': address and address.id, 
                                'phone': address and address.phone,
                                'mobile': address and address.mobile,
                                'section_id': case.section_id and case.section_id.id or False,
                                'description': case.description or False,
                                'phonecall_id': case.id,
                                'priority': case.priority,
                                'type': 'opportunity', 
                                'phone': case.partner_phone or False,
                            })
                vals = {
                            'partner_id': this.partner_id.id,
                            'opportunity_id' : new_opportunity_id,
                            }
                phonecall_obj.write(cr, uid, [case.id], vals)
                phonecall_obj.case_close(cr, uid, [case.id])
                opp_obj.case_open(cr, uid, [new_opportunity_id])

        value = {
            'name': _('Opportunity'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'crm.lead',
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
        record_id = context and context.get('active_id', False) or False
        res = super(crm_phonecall2opportunity, self).default_get(cr, uid, fields, context=context)

        if record_id:
            phonecall = self.pool.get('crm.phonecall').browse(cr, uid, record_id, context=context)
            if 'name' in fields:
                res.update({'name': phonecall.name})
            if 'partner_id' in fields:
                res.update({'partner_id': phonecall.partner_id and phonecall.partner_id.id or False})
        return res

crm_phonecall2opportunity()
