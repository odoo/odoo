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

class crm_claim(osv.osv):
    """
    Crm claim
    """
    _name = "crm.claim"
    _description = "Claim Cases"
    _order = "id desc"
    _inherit = 'crm.case'
    _columns = {
        'date_closed': fields.datetime('Closed', readonly=True),
        'date': fields.datetime('Date'),
        'ref' : fields.reference('Reference', selection=crm._links_get, size=128),
        'ref2' : fields.reference('Reference 2', selection=crm._links_get, size=128),
        'canal_id': fields.many2one('res.partner.canal', 'Channel',\
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
        'categ_id': fields.many2one('crm.case.categ', 'Category',\
                            domain="[('section_id','=',section_id),\
                            ('object_id.model', '=', 'crm.claim')]"),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'type_id': fields.many2one('crm.case.resource.type', 'Claim Type',\
                         domain="[('section_id','=',section_id),\
                         ('object_id.model', '=', 'crm.claim')]"),

        'partner_name': fields.char("Employee's Name", size=64),
        'partner_mobile': fields.char('Mobile', size=32),
        'partner_phone': fields.char('Phone', size=32),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage',\
                         domain="[('section_id','=',section_id),\
                         ('object_id.model', '=', 'crm.claim')]"),
        'probability': fields.float('Probability (%)'),
    }

    _defaults = {
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
    }

crm_claim()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
