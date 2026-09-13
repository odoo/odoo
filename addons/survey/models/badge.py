from odoo import api, fields, models


class GamificationBadge(models.Model):
    _inherit = "gamification.badge"

    survey_ids = fields.One2many(
        comodel_name="survey.survey",
        inverse_name="certification_badge_id",
        string="Survey Ids",
    )
    survey_id = fields.Many2one(
        comodel_name="survey.survey",
        compute="_compute_survey_id",
        store=True,
    )

    @api.depends("survey_ids.certification_badge_id")
    def _compute_survey_id(self) -> None:
        for badge in self:
            badge.survey_id = badge.survey_ids[0] if badge.survey_ids else None
