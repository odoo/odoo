# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

AVAILABLE_PRIORITIES = [
    ('0', 'Low'),
    ('1', 'Medium'),
    ('2', 'High'),
    ('3', 'Very High'),
]


class CrmStage(models.Model):
    """ Model for case stages. This models the main stages of a document
        management flow. Main CRM objects (leads, opportunities, project
        issues, ...) will now use only stages, instead of state and stages.
        Stages are for example used to display the kanban view of records.
    """
    _name = 'crm.stage'
    _description = "CRM Stages"
    _rec_name = 'name'
    _order = "sequence, name, id"

    name = fields.Char('Stage Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=1, help="Used to order stages. Lower is better.")
    is_won = fields.Boolean('Is Won Stage?')
    rotting_threshold_days = fields.Integer('Days to rot', default=0, help='Highlight opportunities that haven\'t been updated for this many days. \
        Set to 0 to disable. Changing this parameter will not affect the rotting status/date of resources last updated before this change.')
    requirements = fields.Text('Requirements', help="Enter here the internal requirements for this stage (ex: Offer sent to customer). It will appear as a tooltip over the stage's name.")
    team_ids = fields.Many2many('crm.team', string='Sales Teams', ondelete='restrict')
    fold = fields.Boolean('Folded in Pipeline',
        help='This stage is folded in the kanban view when there are no records in that stage to display.')
    # This field for interface only
    team_count = fields.Integer('team_count', compute='_compute_team_count')
    color = fields.Integer(string='Color', export_string_translation=False)

    @api.depends('team_ids')
    def _compute_team_count(self):
        self.team_count = self.env['crm.team'].search_count([])

    @api.onchange('is_won')
    def _onchange_is_won(self):
        return {
            'warning': {
                'title': _("Do you really want to update this stage?"),
                'message': _("Changing the value of 'Is Won Stage' may induce a large number of operations, "
                            "as the probabilities of opportunities in this stage will be recomputed on saving."),
            }
        }

    def write(self, vals):
        """ Since leads that are in a won stage must have their
        probability = 100%, this override ensures that setting a stage as won
        will set all the leads in that stage to probability = 100%.
        Inversely, if a won stage is not marked as won anymore, the lead
        probability should be recomputed based on automated probability.
        Note: If a user sets a stage as won and changes his mind right after,
        the manual probability will be lost in the process."""
        res = super().write(vals)
        if 'is_won' in vals:
            won_leads = self.env['crm.lead'].search([('stage_id', 'in', self.ids)])
            if won_leads and vals.get('is_won'):
                won_leads.write({'probability': 100, 'automated_probability': 100})
            elif won_leads and not vals.get('is_won'):
                won_leads._compute_probabilities()
        return res
