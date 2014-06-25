# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
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

import calendar
from datetime import date, datetime
from dateutil import relativedelta

from openerp import tools
from openerp.osv import fields
from openerp.osv import osv

AVAILABLE_PRIORITIES = [
    ('0', 'Very Low'),
    ('1', 'Low'),
    ('2', 'Normal'),
    ('3', 'High'),
    ('4', 'Very High'),
]

class crm_case_channel(osv.osv):
    _name = "crm.case.channel"
    _description = "Channels"
    _order = 'name'
    _columns = {
        'name': fields.char('Channel Name', required=True),
        'active': fields.boolean('Active'),
    }
    _defaults = {
        'active': lambda *a: 1,
    }

class crm_case_stage(osv.osv):
    """ Model for case stages. This models the main stages of a document
        management flow. Main CRM objects (leads, opportunities, project
        issues, ...) will now use only stages, instead of state and stages.
        Stages are for example used to display the kanban view of records.
    """
    _name = "crm.case.stage"
    _description = "Stage of case"
    _rec_name = 'name'
    _order = "sequence"

    _columns = {
        'name': fields.char('Stage Name', required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Used to order stages. Lower is better."),
        'probability': fields.float('Probability (%)', required=True, help="This percentage depicts the default/average probability of the Case for this stage to be a success"),
        'on_change': fields.boolean('Change Probability Automatically', help="Setting this stage will change the probability automatically on the opportunity."),
        'requirements': fields.text('Requirements'),
        'section_ids': fields.many2many('crm.case.section', 'section_stage_rel', 'stage_id', 'section_id', string='Sections',
                        help="Link between stages and sales teams. When set, this limitate the current stage to the selected sales teams."),
        'case_default': fields.boolean('Default to New Sales Team',
                        help="If you check this field, this stage will be proposed by default on each sales team. It will not assign this stage to existing teams."),
        'fold': fields.boolean('Folded in Kanban View',
                               help='This stage is folded in the kanban view when'
                               'there are no records in that stage to display.'),
        'type': fields.selection([('lead', 'Lead'),
                                    ('opportunity', 'Opportunity'),
                                    ('both', 'Both')],
                                    string='Type', required=True,
                                    help="This field is used to distinguish stages related to Leads from stages related to Opportunities, or to specify stages available for both types."),
    }

    _defaults = {
        'sequence': 1,
        'probability': 0.0,
        'on_change': True,
        'fold': False,
        'type': 'both',
        'case_default': True,
    }

class crm_case_categ(osv.osv):
    """ Category of Case """
    _name = "crm.case.categ"
    _description = "Category of Case"
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'object_id': fields.many2one('ir.model', 'Object Name'),
    }
    def _find_object_id(self, cr, uid, context=None):
        """Finds id for case object"""
        context = context or {}
        object_id = context.get('object_id', False)
        ids = self.pool.get('ir.model').search(cr, uid, ['|',('id', '=', object_id),('model', '=', context.get('object_name', False))])
        return ids and ids[0] or False
    _defaults = {
        'object_id' : _find_object_id
    }

class crm_case_resource_type(osv.osv):
    """ Resource Type of case """
    _name = "crm.case.resource.type"
    _description = "Campaign"
    _rec_name = "name"
    _columns = {
        'name': fields.char('Campaign Name', required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }

class crm_payment_mode(osv.osv):
    """ Payment Mode for Fund """
    _name = "crm.payment.mode"
    _description = "CRM Payment Mode"
    _columns = {
        'name': fields.char('Name', required=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
