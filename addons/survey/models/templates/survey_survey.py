import ast

from odoo import api, models, _


class SurveySurvey(models.Model):
    """This model defines additional actions on the 'survey.survey' model that
       can be used to load a survey sample. The model defines a sample for each
       survey type:
       (1) survey: A feedback form
       (2) assessment: A certification
       (3) live_session: A live presentation
       (4) custom: An empty survey
    """

    _inherit = 'survey.survey'

    @api.model
    def action_load_survey_template_sample(self, template_key):
        template_values = self._get_survey_template_values(template_key)
        return self.env['survey.survey'].create(template_values).action_show_sample()

    @api.model
    def get_survey_templates_data(self):
        return {
            'survey': {
                'description': _('Gather feedbacks from your employees and customers'),
                'icon': '/survey/static/src/img/survey_sample_survey.png',
                'template_key': 'survey',
                'title': _('Survey'),
            },
            'assessment': {
                'description': _('Handle quiz & certifications'),
                'icon': '/survey/static/src/img/survey_sample_assessment.png',
                'template_key': 'assessment',
                'title': _('Assessment'),
            },
            'live_session': {
                'description': _('Make your presentations more fun by sharing questions live'),
                'icon': '/survey/static/src/img/survey_sample_live_session.png',
                'template_key': 'live_session',
                'title': _('Live Session'),
            },
        }

    def _get_survey_template_values(self, template_key):
        # Load the correct template
        if template_key == 'survey':
            return self._prepare_survey_template_values()
        elif template_key == 'assessment':
            return self._prepare_assessment_template_values()
        elif template_key == 'live_session':
            return self._prepare_live_session_template_values()
        return {}

    @api.model
    def _prepare_survey_template_values(self):
        return {
            'survey_type': 'survey',
            'title': _('Feedback Form'),
            'description': '<br>'.join([
                _('Please complete this very short survey to let us know how satisfied your are with our products.'),
                _('Your responses will help us improve our product range to serve you even better.')
            ]),
            'description_done': _('Thank you very much for your feedback. We highly value your opinion!'),
            'progression_mode': 'number',
            'questions_layout': 'page_per_question',
            'question_and_page_ids': [
                (0, 0, {  # survey.question
                    'title': _('How frequently do you use our products?'),
                    'question_type': 'simple_choice',
                    'constr_mandatory': True,
                    'suggested_answer_ids': [
                        (0, 0, {  # survey.question.answer
                            'value': _('Often (1-3 times per week)')
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Rarely (1-3 times per month)')
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Never (less than once a month)')
                        })
                    ]
                }),
                (0, 0, {  # survey.question
                    'title': _('How many orders did you pass during the last 6 months?'),
                    'question_type': 'numerical_box',
                }),
                (0, 0, {  # survey.question
                    'title': _('How likely are you to recommend the following products to a friend?'),
                    'question_type': 'matrix',
                    'matrix_subtype': 'simple',
                    'suggested_answer_ids': [
                        (0, 0, {  # survey.question.answer
                            'value': _('Unlikely')
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Neutral')
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Likely')
                        }),
                    ],
                    'matrix_row_ids': [
                        (0, 0, {  # survey.question.answer
                            'value': _('Red Pen')
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Blue Pen')
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Yellow Pen')
                        })
                    ]
                })
            ]
        }

    @api.model
    def _prepare_assessment_template_values(self):
        survey_values = {
            'survey_type': 'assessment',
            'title': _('Certification'),
            'certification': True,
            'access_mode': 'token',
            'is_time_limited': True,
            'time_limit': 15,  # 15 minutes
            'is_attempts_limited': True,
            'attempts_limit': 1,
            'progression_mode': 'number',
            'scoring_type': 'scoring_without_answers',
            'users_can_go_back': True,
            'description': ''.join([
                _('Welcome to this Odoo certification. You will receive 2 random questions out of a pool of 3.'),
                '(<span style="font-style: italic">',
                _('Cheating on your neighbors will not help!'),
                '</span> 😁).<br>',
                _('Good luck!')
            ]),
            'description_done': _('Thank you. We will contact you soon.'),
            'questions_layout': 'page_per_section',
            'questions_selection': 'random',
            'question_and_page_ids': [
                (0, 0, {  # survey.question
                    'title': _('Odoo Certification'),
                    'is_page': True,
                    'question_type': False,
                    'random_questions_count': 2
                }),
                (0, 0, {  # survey.question
                    'title': _('What does "ODOO" stand for?'),
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        (0, 0, {  # survey.question.answer
                            'value': _('It\'s a Belgian word for "Management"')
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Object-Directed Open Organization')
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Organizational Development for Operation Officers')
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('It does not mean anything specific'),
                            'is_correct': True,
                            'answer_score': 10
                        }),
                    ]
                }),
                (0, 0, {  # survey.question
                    'title': _('On Survey questions, one can define "placeholders". But what are they for?'),
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        (0, 0, {  # survey.question.answer
                            'value': _('They are a default answer, used if the participant skips the question')
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('It is a small bit of text, displayed to help participants answer'),
                            'is_correct': True,
                            'answer_score': 10
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('They are technical parameters that guarantees the responsiveness of the page')
                        })
                    ]
                }),
                (0, 0, {  # survey.question
                    'title': _('What does one need to get to pass an Odoo Survey?'),
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        (0, 0, {  # survey.question.answer
                            'value': _('It is an option that can be different for each Survey'),
                            'is_correct': True,
                            'answer_score': 10
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('One needs to get 50% of the total score')
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('One needs to answer at least half the questions correctly')
                        })
                    ]
                }),
            ]
        }
        mail_template = self.env.ref('survey.mail_template_certification', raise_if_not_found=False)
        if mail_template:
            survey_values.update({
                'certification_mail_template_id': mail_template.id
            })
        return survey_values

    @api.model
    def _prepare_live_session_template_values(self):
        return {
            'survey_type': 'live_session',
            'title': _('Live Session'),
            'description': '<br>'.join([
                _('How good of a presenter are you? Let\'s find out!'),
                _('But first, keep listening to the host.')
            ]),
            'description_done': _('Thank you for your participation, hope you had a blast!'),
            'progression_mode': 'number',
            'scoring_type': 'scoring_with_answers',
            'questions_layout': 'page_per_question',
            'session_speed_rating': True,
            'session_speed_rating_time_limit': 90,
            'question_and_page_ids': [
                (0, 0, {  # survey.question
                    'title': _('What is the best way to catch the attention of an audience?'),
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        (0, 0, {  # survey.question.answer
                            'value': _('Speak softly so that they need to focus to hear you')
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Use a fun visual support, like a live presentation'),
                            'is_correct': True,
                            'answer_score': 20
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Show them slides with a ton of text they need to read fast')
                        })
                    ]
                }),
                (0, 0, {  # survey.question
                    'title': _('What is a frequent mistake public speakers do?'),
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        (0, 0, {  # survey.question.answer
                            'value': _('Practice in front of a mirror')
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Speak too fast'),
                            'is_correct': True,
                            'answer_score': 20
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Use humor and make jokes')
                        })
                    ]
                }),
                (0, 0, {  # survey.question
                    'title': _('Why should you consider making your presentation more fun with a small quiz?'),
                    'question_type': 'multiple_choice',
                    'suggested_answer_ids': [
                        (0, 0, {  # survey.question.answer
                            'value': _('It helps attendees focus on what you are saying'),
                            'is_correct': True,
                            'answer_score': 20
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('It is more engaging for your audience'),
                            'is_correct': True,
                            'answer_score': 20
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('It helps attendees remember the content of your presentation'),
                            'is_correct': True,
                            'answer_score': 20
                        })
                    ]
                }),

            ]
        }

    @api.model
    def action_load_sample_custom(self):
        return self.env['survey.survey'].create({
            'survey_type': 'custom',
            'title': '',
        }).action_show_sample()

    def action_show_sample(self):
        action = self.env['ir.actions.act_window']._for_xml_id('survey.action_survey_form')
        action['views'] = [[self.env.ref('survey.survey_survey_view_form').id, 'form']]
        action['res_id'] = self.id
        action['context'] = dict(ast.literal_eval(action.get('context', {})),
            create=False
        )
        return action
