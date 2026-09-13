from odoo import fields, models


class CrmTeam(models.Model):
    _inherit = "crm.team"

    origin_survey_ids = fields.One2many(
        comodel_name="survey.survey",
        inverse_name="team_id",
        string="Survey opportunities related to the sales team",
    )
