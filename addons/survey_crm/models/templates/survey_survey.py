from odoo import Command, api, models


class SurveySurvey(models.Model):
    _inherit = "survey.survey"

    @api.model
    def get_survey_templates_data(self):
        return super().get_survey_templates_data() | {
            "lead_qualification": {
                "description": self.env._("Create leads when key answers are chosen"),
                "icon": "/survey_crm/static/src/img/survey_sample_lead_qualification.svg",
                "template_key": "lead_qualification",
                "title": self.env._("Lead Qualification"),
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
            "title": self.env._("Getting to know you"),
            "description_done": self.env._("Thanks for answering!"),
            "progression_mode": "number",
            "questions_layout": "page_per_question",
            "question_and_page_ids": [
                Command.create(
                    {
                        "title": self.env._(
                            "Let's start with a basic question. What's your email address?"
                        ),
                        "question_type": "char_box",
                        "constr_mandatory": True,
                        "validation_email": True,
                        "save_as_email": True,
                    }
                ),
                Command.create(
                    {
                        "title": self.env._("What is the size of your company?"),
                        "question_type": "simple_choice",
                        "constr_mandatory": True,
                        "suggested_answer_ids": [
                            Command.create(
                                {
                                    "value": self.env._("1-10 employees"),
                                }
                            ),
                            Command.create(
                                {
                                    "value": self.env._("11-100 employees"),
                                    "generate_lead": True,
                                }
                            ),
                            Command.create(
                                {
                                    "value": self.env._("100+ employees"),
                                }
                            ),
                        ],
                    }
                ),
                Command.create(
                    {
                        "title": self.env._(
                            "Which of the following best describes your main goal?"
                        ),
                        "question_type": "simple_choice",
                        "constr_mandatory": True,
                        "suggested_answer_ids": [
                            Command.create(
                                {
                                    "value": self.env._("Improving efficiency"),
                                    "generate_lead": True,
                                }
                            ),
                            Command.create(
                                {
                                    "value": self.env._("Reducing costs"),
                                }
                            ),
                            Command.create(
                                {
                                    "value": self.env._("Expanding sales"),
                                    "generate_lead": True,
                                }
                            ),
                        ],
                    }
                ),
                Command.create(
                    {
                        "title": self.env._(
                            "Who will make the final decision on this purchase?"
                        ),
                        "question_type": "simple_choice",
                        "constr_mandatory": True,
                        "suggested_answer_ids": [
                            Command.create(
                                {"value": self.env._("Me"), "generate_lead": True}
                            ),
                            Command.create(
                                {
                                    "value": self.env._("My Manager/Executive"),
                                    "generate_lead": True,
                                }
                            ),
                            Command.create(
                                {
                                    "value": self.env._("A team/committee"),
                                }
                            ),
                        ],
                    }
                ),
            ],
        }
