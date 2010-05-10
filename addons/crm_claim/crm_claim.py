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

from osv import fields, osv
from crm import crm

class crm_claim(osv.osv, crm.crm_case):
    """
    Crm claim
    """
    _name = "crm.claim"
    _description = "Claim Cases"
    _order = "id desc"
    _inherit = 'mailgate.thread'
    _columns = {
        'id': fields.integer('ID', readonly=True), 
        'name': fields.char('Name', size=128, required=True), 
        'description': fields.text('Description'), 
        'create_date': fields.datetime('Creation Date' , readonly=True), 
        'write_date': fields.datetime('Update Date' , readonly=True), 
        'date_deadline': fields.date('Deadline'), 
        'date_closed': fields.datetime('Closed', readonly=True), 
        'date': fields.datetime('Date'), 
        'ref' : fields.reference('Reference', selection=crm._links_get, size=128), 
        'ref2' : fields.reference('Reference 2', selection=crm._links_get, size=128), 
        'canal_id': fields.many2one('res.partner.canal', 'Channel', \
                     help="The channels represent the different communication\
                      modes available with the customer." \
                     " With each commercial opportunity, you can indicate the\
                      canall which is this opportunity source."), 
        'planned_revenue': fields.float('Planned Revenue'), 
        'planned_cost': fields.float('Planned Costs'), 
        'som': fields.many2one('res.partner.som', 'State of Mind', \
                        help="The minds states allow to define a value scale which represents" \
                              "the partner mentality in relation to our services.The scale has" \
                              "to be created with a factor for each level from 0 (Very dissatisfied) \
                              to 10 (Extremely satisfied)."), 
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
                            domain="[('section_id','=',section_id),\
                            ('object_id.model', '=', 'crm.claim')]"), 
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'), 
        'type_id': fields.many2one('crm.case.resource.type', 'Claim Type', \
                         domain="[('section_id','=',section_id),\
                         ('object_id.model', '=', 'crm.claim')]"), 
        'user_id': fields.many2one('res.users', 'Responsible'), 
        'section_id': fields.many2one('crm.case.section', 'Sales Team', \
                        select=True, help='Sales team to which Case belongs to.\
                             Define Responsible user and Email account for mail gateway.'), 
        'company_id': fields.many2one('res.company', 'Company'), 
        'partner_id': fields.many2one('res.partner', 'Partner'), 
        'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact', \
                                 domain="[('partner_id','=',partner_id)]"), 
        'email_cc': fields.text('Watchers Emails', size=252 , help="These people\
 will receive a copy of the future" \
" communication between partner and users by email"), 
        'email_from': fields.char('Email', size=128, help="These people will receive email."), 
        'partner_name': fields.char("Employee's Name", size=64), 
        'partner_mobile': fields.char('Mobile', size=32), 
        'partner_phone': fields.char('Phone', size=32), 
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', \
                         domain="[('section_id','=',section_id),\
                         ('object_id.model', '=', 'crm.claim')]"), 
        'probability': fields.float('Probability (%)'), 
        'state': fields.selection(crm.AVAILABLE_STATES, 'State', size=16, readonly=True, 
                                  help='The state is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the state is set to \'Open\'.\
                                  \nWhen the case is over, the state is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the state is set to \'Pending\'.'), 
    }

    _defaults = {
        'active': lambda *a: 1, 
        'user_id': crm.crm_case._get_default_user, 
        'partner_id': crm.crm_case._get_default_partner, 
        'partner_address_id': crm.crm_case._get_default_partner_address, 
        'email_from':crm.crm_case. _get_default_email, 
        'state': lambda *a: 'draft', 
        'section_id':crm.crm_case. _get_section, 
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.case', context=c), 
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0], 
    }

crm_claim()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
