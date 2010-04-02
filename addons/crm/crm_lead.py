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

from osv import fields,osv,orm
import crm

class crm_lead(osv.osv):
    _name = "crm.lead"
    _description = "Leads Cases"
    _order = "priority desc, id desc"
    _inherit = ['res.partner.address','crm.case']
    _columns = {
        'categ_id': fields.many2one('crm.case.categ', 'Lead Source', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.opportunity')]"),
        'type_id': fields.many2one('crm.case.resource.type', 'Lead Type', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.lead')]"),
        'partner_name': fields.char("Contact Name", size=64),

        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'date_closed': fields.datetime('Closed', readonly=True),
        'stage_id': fields.many2one('crm.case.stage', 'Stage', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.lead')]"),
        'opportunity_id': fields.many2one('crm.opportunity', 'Opportunity'),

        'user_id': fields.many2one('res.users', 'Salesman'),
        'referred': fields.char('Referred By', size=32),
        'function_name' : fields.char('Function', size=64),
    }
    _defaults = {
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.lead', context=c),
    }
crm_lead()
