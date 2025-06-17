from odoo import api, models, _


class SurveySurvey(models.Model):
    """This class adds the "Lead qualification" button to the view to the "not found" page."""
    _inherit = 'survey.survey'

    @api.model
    def get_survey_type_templates_data(self):
        return super().get_survey_type_templates_data() | {
            'lead_qualification': {
                'description': _("Create leads when key answers are chosen"),
                'icon': '/survey/static/src/img/survey_sample_lead_qualification.svg',
                'template_key': 'lead_qualification',
                'title': _("Lead Qualification"),
            },
        }

    def _get_survey_type_template_values(self, template_key):
        if template_key == 'lead_qualification':
            return self._prepare_lead_qualification_template_values()
        else:
            return super()._get_survey_type_template_values(template_key)

    @api.model
    def _prepare_lead_qualification_template_values(self):
        return {
            'survey_type': 'survey',
            'title': _('Getting to know you'),
            'description_done': _('Thanks for answering!'),
            'progression_mode': 'number',
            'questions_layout': 'page_per_question',
            'question_and_page_ids': [
                (0, 0, {  # survey.question
                    'title': _('What is the size of your company?'),
                    'question_type': 'simple_choice',
                    'constr_mandatory': True,
                    'suggested_answer_ids': [
                        (0, 0, {  # survey.question.answer
                            'value': _('1-10 employees'),
                            'is_create_lead': False
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('11-100 employees'),
                            'is_create_lead': True
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('100+ employees'),
                            'is_create_lead': False
                        })
                    ]
                }),
                (0, 0, {  # survey.question
                    'title': _('Which of the following best describes your main goal?'),
                    'question_type': 'simple_choice',
                    'constr_mandatory': True,
                    'suggested_answer_ids': [
                        (0, 0, {  # survey.question.answer
                            'value': _('Improving efficiency'),
                            'is_create_lead': True
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Reducing costs'),
                            'is_create_lead': False
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Expanding sales'),
                            'is_create_lead': True
                        })
                    ]
                }),
                (0, 0, {  # survey.question
                    'title': _('Who will make the final decision on this purchase?'),
                    'question_type': 'simple_choice',
                    'constr_mandatory': True,
                    'suggested_answer_ids': [
                        (0, 0, {  # survey.question.answer
                            'value': _('Me'),
                            'is_create_lead': True
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('My Manager/Executive'),
                            'is_create_lead': True
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('A team/committee'),
                            'is_create_lead': False
                        })
                    ]
                }),
            ]
        }
