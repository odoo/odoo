from odoo import fields, models


class TeamTeam(models.Model):
    _inherit = "team.team"

    origin_survey_ids = fields.One2many(
        comodel_name="survey.survey",
        inverse_name="team_id",
        string="Survey opportunities related to the sales team",
    )
