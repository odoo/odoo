# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import api, models, _


class SurveyTemplate(models.Model):
    """This model defines additional actions on the 'survey.survey' model that
       can be used to load a survey sample. The model defines a sample for:
       (1) A feedback form
       (2) A certification
       (3) A live presentation
    """

    _inherit = 'survey.survey'

    @api.model
    def action_load_sample_feedback_form(self):
        return self.env['survey.survey'].create({
            'title': _('Feedback Form'),
            'description': _('What do you think of our new eShop? Let us hear your voice!'),
            'description_done': _('Thank you very much for your feedback. We at MyCompany value your opinion!'),
            'progression_mode': 'number',
            'questions_layout': 'one_page',
            'question_and_page_ids': [
                (0, 0, { # survey.question
                    'title': _('About you'),
                    'is_page': True,
                    'question_type': False
                }),
                (0, 0, { # survey.question
                    'title': _('How frequently do you buy products online?'),
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        (0, 0, { # survey.question.answer
                            'value': _('Once a day')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('Once a week')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('Once a month')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('Once a year')
                        }),
                        (0, 0, {  # survey.question.answer
                            'value': _('Never')
                        })
                    ]
                }),
                (0, 0, { # survey.question
                    'title': _('How many times did you order products on our website?'),
                    'question_type': 'numerical_box'
                }),
                (0, 0, { # survey.question
                    'title': _('About our ecommerce'),
                    'is_page': True,
                    'question_type': False
                }),
                (0, 0, { # survey.question
                    'title': _('What do you think about our new eCommerce?'),
                    'question_type': 'matrix',
                    'matrix_subtype': 'simple',
                    'suggested_answer_ids': [
                        (0, 0, { # survey.question.answer
                            'value': _('Strongly disagree')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('Disagree')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('Neutral')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('Agree')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('Strongly agree')
                        })
                    ],
                    'matrix_row_ids': [
                        (0, 0, { # survey.question.answer
                            'value': _('The new layout and design is fresh and up-to-date')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('It is easy to find the product that I want')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('The tool to compare the products is useful to make a choice')
                        })
                    ]
                })
            ]
        }).action_show_sample()

    @api.model
    def action_load_sample_certification(self):
        survey_values = {
            'title': _('Certification'),
            'certification': True,
            'access_mode': 'token',
            'is_time_limited': True,
            'time_limit': 15, # 15 minutes
            'is_attempts_limited': True,
            'attempts_limit': 1,
            'progression_mode': 'number',
            'scoring_type': 'scoring_without_answers',
            'users_can_go_back': True,
            'description': '<br>'.join([
                _('Welcome to the History certification. You will receive 2 random questions.'),
                _('Good luck!')
            ]),
            'description_done': _('Thank you. We will contact you soon.'),
            'questions_layout': 'page_per_section',
            'questions_selection': 'random',
            'question_and_page_ids': [
                (0, 0, { # survey.question
                    'title': _('History'),
                    'is_page': True,
                    'question_type': False,
                    'random_questions_count': 2
                }),
                (0, 0, { # survey.question
                    'title': _('When did Genghis Khan die?'),
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        (0, 0, { # survey.question.answer
                            'value': _('1227'),
                            'is_correct': True,
                            'answer_score': 10
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('1324')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('1055')
                        })
                    ]
                }),
                (0, 0, { # survey.question
                    'title': _('Who is the architect of the Great Pyramid of Giza ?'),
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        (0, 0, { # survey.question.answer
                            'value': _('Imhotep')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('Amenhotep')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('Hemiunu'),
                            'is_correct': True,
                            'answer_score': 10
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('Papyrus')
                        })
                    ]
                }),
                (0, 0, { # survey.question
                    'title': _('How many years did the 100 years war last?'),
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        (0, 0, { # survey.question.answer
                            'value': _('99 years')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('100 years')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('116 years'),
                            'is_correct': True,
                            'answer_score': 10
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('127 years')
                        })
                    ]
                })
            ]
        }
        mail_template = self.env.ref('survey.mail_template_certification', raise_if_not_found=False)
        if mail_template:
            survey_values.update({
                'certification_mail_template_id': mail_template.id
            })
        return self.env['survey.survey'].create(survey_values).action_show_sample()

    @api.model
    def action_load_sample_live_presentation(self):
        return self.env['survey.survey'].create({
            'title': _('Live Presentation'),
            'description': '<br>'.join([
                _('How well do you know trees? Let\'s find out!'),
                _('But first, keep listening to the host.')
            ]),
            'description_done': _('Thank you for your participation, hope you had a blast!'),
            'progression_mode': 'number',
            'scoring_type': 'scoring_with_answers',
            'questions_layout': 'page_per_question',
            'session_speed_rating': True,
            'question_and_page_ids': [
                (0, 0, { # survey.question
                    'title': _('About you'),
                    'is_page': True,
                    'question_type': False
                }),
                (0, 0, { # survey.question
                    'title': _('Pick a nickname'),
                    'question_type': 'char_box',
                    'save_as_nickname': True
                }),
                (0, 0, { # survey.question
                    'title': _('Quiz'),
                    'is_page': True,
                    'question_type': False
                }),
                (0, 0, { # survey.question
                    'title': _('In which country did the bonsai technique develop?'),
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        (0, 0, { # survey.question.answer
                            'value': _('Japan'),
                            'is_correct': True,
                            'answer_score': 20
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('China')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('Vietnam')
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('South Korea')
                        })
                    ]
                }),
                (0, 0, { # survey.question
                    'title': _('In the list below, select all the coniferous.'),
                    'question_type': 'multiple_choice',
                    'suggested_answer_ids': [
                        (0, 0, { # survey.question.answer
                            'value': _('Douglas Fir'),
                            'is_correct': True,
                            'answer_score': 5
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('Norway Spruce'),
                            'is_correct': True,
                            'answer_score': 5
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('European Yew'),
                            'is_correct': True,
                            'answer_score': 5
                        }),
                        (0, 0, { # survey.question.answer
                            'value': _('Mountain Pine'),
                            'is_correct': True,
                            'answer_score': 5
                        })
                    ]
                })
            ]
        }).action_show_sample()

    def action_show_sample(self):
        action = self.env['ir.actions.act_window']._for_xml_id('survey.action_survey_form')
        action['target'] = 'main'
        action['views'] = [[self.env.ref('survey.survey_survey_view_form').id, 'form']]
        action['res_id'] = self.id
        action['context'] = dict(ast.literal_eval(action.get('context', {})),
            form_view_initial_mode='edit',
            create=False
        )
        return action
