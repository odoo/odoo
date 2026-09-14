from odoo import _, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SurveyUser_Input(models.Model):
    _inherit = "survey.user_input"

    applicant_id = fields.Many2one(
        comodel_name="hr.applicant",
        index="btree_not_null",
    )

    def _mark_done(self):
        odoobot = self.env.ref("base.partner_root")
        for user_input in self:
            if user_input.applicant_id:
                body = _(
                    'The applicant "%s" has finished the survey.',
                    user_input.applicant_id.partner_name,
                )
                _debug.lifecycle(
                    "survey_completed",
                    applicant=user_input.applicant_id,
                    survey=user_input.survey_id,
                )
                user_input.applicant_id.message_post(body=body, author_id=odoobot.id)
        return super()._mark_done()
