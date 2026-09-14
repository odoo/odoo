from odoo import _, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrJob(models.Model):
    _inherit = "hr.job"

    survey_id = fields.Many2one(
        comodel_name="survey.survey",
        string="Interview Form",
        index="btree_not_null",
        help="Choose an interview form for this job position and you will be able to print/answer this interview from all applicants who apply for this job",
    )

    def action_test_survey(self):
        self.check_singleton()
        return self.survey_id.action_test_survey()

    def action_new_survey(self):
        self.check_singleton()
        survey = self.env["survey.survey"].create(
            {
                "title": _("Interview Form: %s", self.name),
                "survey_type": "recruitment",
            }
        )
        _debug.lifecycle("interview_form_created", job=self, survey=survey)
        self.write({"survey_id": survey.id})

        return {
            "name": _("Survey"),
            "view_mode": "form,list",
            "res_model": "survey.survey",
            "type": "ir.actions.act_window",
            "res_id": survey.id,
        }
