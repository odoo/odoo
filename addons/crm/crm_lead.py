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
    _order = "id desc"
    _inherit = 'crm.case'
    _columns = {
         'name': fields.char('Lead Subject', size=64),
         'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.opportunity')]"),
         'type_id': fields.many2one('crm.case.resource.type', 'Lead Type Name', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.lead')]"),

         'partner_name': fields.char("Lead Name", size=64),
        'function': fields.many2one('res.partner.function', 'Function'),
         'partner_address': fields.char("Address", size=64),
         'partner_contact': fields.char('Contact', size=64),
         'partner_phone': fields.char('Phone', size=32),
         'partner_mobile': fields.char('Mobile', size=32),

        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state_id': fields.many2one("res.country.state", 'Fed. State', domain="[('country_id','=',country_id)]"),
        'country_id': fields.many2one('res.country', 'Country'),

         'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
         'probability': fields.float('Probability (%)'),
         'date_closed': fields.datetime('Closed', readonly=True),
         'ref' : fields.reference('Reference', selection=crm._links_get, size=128),
         'ref2' : fields.reference('Reference 2', selection=crm._links_get, size=128),
         'canal_id': fields.many2one('res.partner.canal', 'Channel',help="The channels represent the different communication modes available with the customer." \
                                                                         " With each commercial opportunity, you can indicate the canall which is this opportunity source."),
         'planned_revenue': fields.float('Planned Revenue'),
         'planned_cost': fields.float('Planned Costs'),
         'stage_id': fields.many2one('crm.case.stage', 'Stage', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.lead')]"),
         'som': fields.many2one('res.partner.som', 'State of Mind', help="The minds states allow to define a value scale which represents" \
                                                                    "the partner mentality in relation to our services.The scale has" \
                                                                    "to be created with a factor for each level from 0 (Very dissatisfied) to 10 (Extremely satisfied)."),
         'opportunity_id': fields.many2one('crm.opportunity', 'Opportunity'),

         'user_id': fields.many2one('res.users', 'Salesman'),
         'referred': fields.char('Referred By', size=32),
    }
crm_lead()
