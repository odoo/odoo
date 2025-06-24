from odoo import fields, models


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    # Origin of leads
    origin_survey_ids = fields.One2many(
        'survey.survey', 'team_id',
        string='Survey opportunities related to the sales team')
