from odoo import _, api, models


class SurveySurvey(models.Model):
    _inherit = "survey.survey"

    @api.model
    def get_survey_templates_data(self):
        return super().get_survey_templates_data() | {
            "lead_qualification": {
                "description": _("Create leads when key answers are chosen"),
                "icon": "/survey_crm/static/src/img/survey_sample_lead_qualification.svg",
                "template_key": "lead_qualification",
                "title": _("Lead Qualification"),
            },
        }

    def _prepare_template_vals(self, template_key):
        if template_key == "lead_qualification":
            return self._prepare_lead_qualification_template_values()
        return super()._prepare_template_vals(template_key)

    @api.model
    def _prepare_lead_qualification_template_values(self):
        return {
            "survey_type": "survey",
            "title": _("Getting to know you"),
            "description_done": _("Thanks for answering!"),
            "progression_mode": "number",
            "questions_layout": "page_per_question",
            "question_and_page_ids": [
                (
                    0,
                    0,
                    {
                        "title": _(
                            "Let's start with a basic question. What's your email address?"
                        ),
                        "question_type": "char_box",
                        "constr_mandatory": True,
                        "validation_email": True,
                        "save_as_email": True,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "title": _("What is the size of your company?"),
                        "question_type": "simple_choice",
                        "constr_mandatory": True,
                        "suggested_answer_ids": [
                            (
                                0,
                                0,
                                {
                                    "value": _("1-10 employees"),
                                },
                            ),
                            (
                                0,
                                0,
                                {"value": _("11-100 employees"), "generate_lead": True},
                            ),
                            (
                                0,
                                0,
                                {
                                    "value": _("100+ employees"),
                                },
                            ),
                        ],
                    },
                ),
                (
                    0,
                    0,
                    {
                        "title": _(
                            "Which of the following best describes your main goal?"
                        ),
                        "question_type": "simple_choice",
                        "constr_mandatory": True,
                        "suggested_answer_ids": [
                            (
                                0,
                                0,
                                {
                                    "value": _("Improving efficiency"),
                                    "generate_lead": True,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "value": _("Reducing costs"),
                                },
                            ),
                            (
                                0,
                                0,
                                {"value": _("Expanding sales"), "generate_lead": True},
                            ),
                        ],
                    },
                ),
                (
                    0,
                    0,
                    {
                        "title": _(
                            "Who will make the final decision on this purchase?"
                        ),
                        "question_type": "simple_choice",
                        "constr_mandatory": True,
                        "suggested_answer_ids": [
                            (0, 0, {"value": _("Me"), "generate_lead": True}),
                            (
                                0,
                                0,
                                {
                                    "value": _("My Manager/Executive"),
                                    "generate_lead": True,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "value": _("A team/committee"),
                                },
                            ),
                        ],
                    },
                ),
            ],
        }
