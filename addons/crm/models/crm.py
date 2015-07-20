# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models

AVAILABLE_PRIORITIES = [
    ('0', 'Normal'),
    ('1', 'Low'),
    ('2', 'High'),
    ('3', 'Very High'),
]

class CrmStage(models.Model):
    """ Model for case stages. This models the main stages of a document
        management flow. Main CRM objects (leads, opportunities, project
        issues, ...) will now use only stages, instead of state and stages.
        Stages are for example used to display the kanban view of records.
    """
    _name = "crm.stage"
    _description = "Stage of case"
    _rec_name = 'name'
    _order = "sequence"

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(help="Used to order stages. Lower is better.", default=1)
    probability = fields.Float(string='Probability (%)', required=True, help="This percentage depicts the default/average probability of the Case for this stage to be a success", default=1.0)
    on_change = fields.Boolean(string='Change Probability Automatically', help="Setting this stage will change the probability automatically on the opportunity.")
    requirements = fields.Text('Requirements')
    team_ids = fields.Many2many('crm.team', 'crm_team_stage_rel', 'stage_id', 'team_id', string='Teams',
                    help="Link between stages and sales teams. When set, this limitate the current stage to the selected sales teams.")
    case_default = fields.Boolean(string='Default to New Sales Team',
                    help="If you check this field, this stage will be proposed by default on each sales team. It will not assign this stage to existing teams.", default=True)
    legend_priority = fields.Text(string='Priority Management Explanation', translate=True,
        help='Explanation text to help users using the star and priority mechanism on stages or issues that are in this stage.')
    fold = fields.Boolean(string='Folded in Kanban View',
                           help='This stage is folded in the kanban view when'
                           'there are no records in that stage to display.')
    stage_type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity'), ('both', 'Both')],
                             required=True,
                             help="This field is used to distinguish stages related to Leads from stages related to Opportunities, or to specify stages available for both types.", default='both', oldname="type", string="Stage Type")
