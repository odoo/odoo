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

from openerp.osv import osv, fields
from openerp.http import request

AVAILABLE_PRIORITIES = [
    ('0', 'Normal'),
    ('1', 'Low'),
    ('2', 'High'),
    ('3', 'Very High'),
]

class crm_stage(osv.Model):
    """ Model for case stages. This models the main stages of a document
        management flow. Main CRM objects (leads, opportunities, project
        issues, ...) will now use only stages, instead of state and stages.
        Stages are for example used to display the kanban view of records.
    """
    _name = "crm.stage"
    _description = "Stage of case"
    _rec_name = 'name'
    _order = "sequence"

    _columns = {
        'name': fields.char('Stage Name', required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Used to order stages. Lower is better."),
        'probability': fields.float('Probability (%)', required=True, help="This percentage depicts the default/average probability of the Case for this stage to be a success"),
        'on_change': fields.boolean('Change Probability Automatically', help="Setting this stage will change the probability automatically on the opportunity."),
        'requirements': fields.text('Requirements'),
        'team_ids': fields.many2many('crm.team', 'crm_team_stage_rel', 'stage_id', 'team_id', string='Teams',
                        help="Link between stages and sales teams. When set, this limitate the current stage to the selected sales teams."),
        'case_default': fields.boolean('Default to New Sales Team',
                        help="If you check this field, this stage will be proposed by default on each sales team. It will not assign this stage to existing teams."),
        'legend_priority': fields.text(
            'Priority Management Explanation', translate=True,
            help='Explanation text to help users using the star and priority mechanism on stages or issues that are in this stage.'),
        'fold': fields.boolean('Folded in Kanban View',
                               help='This stage is folded in the kanban view when'
                               'there are no records in that stage to display.'),
        'type': fields.selection([('lead', 'Lead'), ('opportunity', 'Opportunity'), ('both', 'Both')],
                                 string='Type', required=True,
                                 help="This field is used to distinguish stages related to Leads from stages related to Opportunities, or to specify stages available for both types."),
    }

    _defaults = {
        'sequence': 1,
        'probability': 1.0,
        'fold': False,
        'type': 'both',
        'case_default': True,
    }
