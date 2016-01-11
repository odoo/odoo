# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

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

    @api.model
    def default_get(self, fields):
        ctx = dict(self.env.context)
        if ctx.get('default_team_id') and not ctx.get('crm_team_mono', False):
            ctx.pop('default_team_id')
        return super(CrmStage, self.with_context(ctx)).default_get(fields)

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=1, help="Used to order stages. Lower is better.")
    probability = fields.Float(string='Probability (%)', required=True, default=10.0, help="This percentage depicts the default/average probability of the Case for this stage to be a success")
    on_change = fields.Boolean(string='Change Probability Automatically', help="Setting this stage will change the probability automatically on the opportunity.")
    requirements = fields.Text(string='Requirements', help="Enter here the internal requirements for this stage (ex: Offer sent to customer). It will appear as a tooltip over the stage's name.")
    team_id = fields.Many2one('crm.team', string='Team',
                               ondelete='set null',
                               help='Specific team that uses this stage. Other teams will not ne able to see or use this stage.')
    legend_priority = fields.Text(string='Priority Management Explanation', translate=True,
        help='Explanation text to help users using the star and priority mechanism on stages or issues that are in this stage.')
    fold = fields.Boolean(string='Folded in Pipeline', default=False,
                           help='This stage is folded in the kanban view when '
                           'there are no records in that stage to display.')
