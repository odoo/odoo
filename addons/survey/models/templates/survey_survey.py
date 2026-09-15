import copy
from typing import Any

from odoo import _, api, models

from . import samples


class SurveySurvey(models.Model):
    _inherit = "survey.survey"

    @api.model
    def action_load_survey_template_sample(self, template_key: str) -> dict[str, Any]:
        template_values = self._prepare_template_vals(template_key)
        return self.env["survey.survey"].create(template_values).action_show_sample()

    @api.model
    def get_survey_templates_data(self) -> dict[str, dict[str, Any]]:
        return {
            "survey": {
                "description": _("Gather feedbacks from your employees and customers"),
                "icon": "/survey/static/src/img/survey_sample_survey.png",
                "template_key": "survey",
                "title": _("Survey"),
            },
            "assessment": {
                "description": _("Handle quiz & certifications"),
                "icon": "/survey/static/src/img/survey_sample_assessment.png",
                "template_key": "assessment",
                "title": _("Assessment"),
            },
            "live_session": {
                "description": _(
                    "Make your presentations more fun by sharing questions live"
                ),
                "icon": "/survey/static/src/img/survey_sample_live_session.png",
                "template_key": "live_session",
                "title": _("Live Session"),
            },
        }

    def _prepare_template_vals(self, template_key: str) -> dict[str, Any]:
        if template_key == "survey":
            return self._prepare_survey_template_values()
        elif template_key == "assessment":
            return self._prepare_assessment_template_values()
        elif template_key == "live_session":
            return self._prepare_live_session_template_values()
        return {}

    @api.model
    def _prepare_survey_template_values(self) -> dict[str, Any]:
        return copy.deepcopy(samples.SURVEY_SAMPLE)

    @api.model
    def _prepare_assessment_template_values(self) -> dict[str, Any]:
        values = copy.deepcopy(samples.ASSESSMENT_SAMPLE)
        mail_template = self.env.ref(
            "survey.mail_template_certification", raise_if_not_found=False
        )
        if mail_template:
            values["certification_mail_template_id"] = mail_template.id
        return values

    @api.model
    def _prepare_live_session_template_values(self) -> dict[str, Any]:
        return copy.deepcopy(samples.LIVE_SESSION_SAMPLE)

    @api.model
    def action_load_sample_custom(self) -> dict[str, Any]:
        return (
            self.env["survey.survey"]
            .create(
                {
                    "survey_type": "custom",
                    "title": "",
                }
            )
            .action_show_sample()
        )

    def action_show_sample(self) -> dict[str, Any]:
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "survey.action_survey_form"
        )
        action["views"] = [[self.env.ref("survey.survey_survey_view_form").id, "form"]]
        action["res_id"] = self.id
        action["context"] = dict(
            self.env["ir.actions.actions"]._eval_action_context(
                action.get("context", "{}")
            ),
            create=False,
        )
        return action
