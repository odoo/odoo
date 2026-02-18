from odoo import models


class SurveyInvite(models.TransientModel):
    _inherit = "survey.invite"

    def _get_survey_inputs(self):
        return self.survey_id.user_input_ids.filtered(
            lambda s: s.state != 'cancelled',
        )
