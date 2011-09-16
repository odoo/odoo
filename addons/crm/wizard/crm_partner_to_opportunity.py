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

class crm_partner2opportunity(osv.osv_memory):
    """Converts Partner To Opportunity"""

    _name = 'crm.partner2opportunity'
    _description = 'Partner To Opportunity'

    _columns = {
        'name' : fields.char('Opportunity Name', size=64, required=True),
        'planned_revenue': fields.float('Expected Revenue', digits=(16,2)),
        'probability': fields.float('Success Probability', digits=(16,2)),
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
        partner_obj = self.pool.get('res.partner')
        data = context and context.get('active_ids', []) or []
        res = super(crm_partner2opportunity, self).default_get(cr, uid, fields, context=context)

        for partner in partner_obj.browse(cr, uid, data, []):
            if 'name' in fields:
                res.update({'name': partner.name})
            if 'partner_id' in fields:
                res.update({'partner_id': data and data[0] or False})
        return res

    def make_opportunity(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """

        data = context and context.get('active_ids', []) or []
        make_opportunity = self.pool.get('crm.partner2opportunity')
        data_obj = self.pool.get('ir.model.data')
        part_obj = self.pool.get('res.partner')
        categ_obj = self.pool.get('crm.case.categ')
        case_obj = self.pool.get('crm.lead')
        
        for make_opportunity_obj in make_opportunity.browse(cr, uid, ids, context=context):
            result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_opportunities_filter')
            res = data_obj.read(cr, uid, result, ['res_id'])

            id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_form_view_oppor')
            id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_tree_view_oppor')
            if id2:
                id2 = data_obj.browse(cr, uid, id2, context=context).res_id
            if id3:
                id3 = data_obj.browse(cr, uid, id3, context=context).res_id

            address = part_obj.address_get(cr, uid, data)
            categ_ids = categ_obj.search(cr, uid, [('object_id.model','=','crm.lead')])

            opp_id = case_obj.create(cr, uid, {
                'name' : make_opportunity_obj.name,
                'planned_revenue' : make_opportunity_obj.planned_revenue,
                'probability' : make_opportunity_obj.probability,
                'partner_id' : make_opportunity_obj.partner_id.id,
                'partner_address_id' : address['default'],
                'categ_id' : categ_ids and categ_ids[0] or '',
                'state' :'draft',
                'type': 'opportunity'
            })
            value = {
                'name' : _('Opportunity'),
                'view_type' : 'form',
                'view_mode' : 'form,tree',
                'res_model' : 'crm.lead',
                'res_id' : opp_id,
                'view_id' : False,
                'views' : [(id2, 'form'), (id3, 'tree'), (False, 'calendar'), (False, 'graph')],
                'type' : 'ir.actions.act_window',
                'search_view_id' : res['res_id']
            }
            return value

crm_partner2opportunity()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
