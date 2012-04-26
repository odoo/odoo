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

from osv import fields,osv
from tools.translate import _

class res_partner(osv.osv):
    """ Inherits partner and adds CRM information in the partner form """
    _inherit = 'res.partner'
    
    def _total_oppo(self, cr, uid, ids, field_name, arg, context=None):
        total_oppo={}
        oppo_pool=self.pool.get('crm.lead')
        for id in ids:
            oppo_ids = oppo_pool.search(cr, uid, [('partner_id', '=', id)])
            total_oppo[id] = len(oppo_ids)
        return total_oppo

    def _total_meeting(self, cr, uid, ids, field_name, arg, context=None):
        total_meeting={}
        meeting_pool=self.pool.get('crm.meeting')
        for id in ids:
            meeting_ids = meeting_pool.search(cr, uid, [('partner_id', '=', id)])
            total_meeting[id] = len(meeting_ids)
        return total_meeting
    
    
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'opportunity_ids': fields.one2many('crm.lead', 'partner_id',\
            'Leads and Opportunities'),
        'meeting_ids': fields.one2many('crm.meeting', 'partner_id',\
            'Meetings'),
        'phonecall_ids': fields.one2many('crm.phonecall', 'partner_id',\
            'Phonecalls'),
        'total_oppo': fields.function(_total_oppo , type='integer',string="Total Opportunity"),
        'total_meeting': fields.function(_total_meeting , type='integer',string="Total Meeting"),
    }

    _defaults = {
        'total_oppo': 0,
        'total_meeting': 0,
    }

    def redirect_partner_form(self, cr, uid, partner_id, context=None):
        search_view = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'view_res_partner_filter')
        value = {
            'domain': "[]",
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'res.partner',
            'res_id': int(partner_id),
            'view_id': False,
            'context': context,
            'type': 'ir.actions.act_window',
            'search_view_id': search_view and search_view[1] or False
        }
        return value

    def get_opportunity(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        models_data = self.pool.get('ir.model.data')

        form_view = models_data.get_object_reference(cr, uid, 'crm', 'crm_case_form_view_oppor')
        tree_view = models_data.get_object_reference(cr, uid, 'crm', 'crm_case_tree_view_oppor')
        search_view = models_data.get_object_reference(cr, uid, 'crm', 'view_crm_case_opportunities_filter')
        partner_id = self.browse(cr, uid, ids[0], context=context)
        domain =[('partner_id', '=', partner_id.id)]

        return {
                'name': _('Opportunity'),
                'view_type': 'form',
                'view_mode': 'tree, form',
                'res_model': 'crm.lead',
                'domain': domain,
                'view_id': False,
                'views': [(tree_view and tree_view[1] or False, 'tree'),
                          (form_view and form_view[1] or False, 'form'),
                          (False, 'calendar'), (False, 'graph')],
                'type': 'ir.actions.act_window',
                'search_view_id': search_view and search_view[1] or False,
                'nodestroy': True,
        }

    def make_opportunity(self, cr, uid, ids, opportunity_summary, planned_revenue=0.0, probability=0.0, partner_id=None, context=None):
        categ_obj = self.pool.get('crm.case.categ')
        categ_ids = categ_obj.search(cr, uid, [('object_id.model','=','crm.lead')])
        lead_obj = self.pool.get('crm.lead')
        opportunity_ids = {}
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner_id:
                partner_id = partner.id
            opportunity_id = lead_obj.create(cr, uid, {
                'name' : opportunity_summary,
                'planned_revenue' : planned_revenue,
                'probability' : probability,
                'partner_id' : partner_id,
                'categ_id' : categ_ids and categ_ids[0] or '',
                'state' :'draft',
                'type': 'opportunity'
            }, context=context)
            opportunity_ids[partner_id] = opportunity_id
        return opportunity_ids
res_partner()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
