# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo import Command
from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUiFeedback(HttpCaseWithUserDemo):

    def setUp(self):
        super(TestUiFeedback, self).setUp()
        self.survey_feedback = self.env['survey.survey'].create({
            'title': 'User Feedback Form',
            'access_token': 'b137640d-14d4-4748-9ef6-344caaaaaae',
            'access_mode': 'public',
            'users_can_go_back': True,
            'questions_layout': 'page_per_section',
            'description': """<p>This survey allows you to give a feedback about your experience with our eCommerce solution.
    Filling it helps us improving your experience.</p></field>""",
            'question_and_page_ids': [
                (0, 0, {
                    'title': 'General information',
                    'sequence': 1,
                    'question_type': False,
                    'is_page': True,
                    'description': """<p>This section is about general information about you. Answering them helps qualifying your answers.</p>""",
                }), (0, 0, {
                    'title': 'Where do you live?',
                    'sequence': 2,
                    'question_type': 'char_box',
                    'constr_mandatory': False,
                }), (0, 0, {
                    'title': 'When is your date of birth?',
                    'sequence': 3,
                    'question_type': 'date',
                    'description': False,
                }), (0, 0, {
                    'title': 'How frequently do you buy products online?',
                    'sequence': 4,
                    'question_type': 'simple_choice',
                    'comments_allowed': True,
                    'comment_count_as_answer': True,
                    'constr_mandatory': True,
                    'suggested_answer_ids': [
                        (0, 0, {
                            'value': 'Once a day',
                            'sequence': 1,
                        }), (0, 0, {
                            'value': 'Once a week',
                            'sequence': 2,
                        }), (0, 0, {
                            'value': 'Once a month',
                            'sequence': 3,
                        }), (0, 0, {
                            'value': 'Once a year',
                            'sequence': 4,
                        }), (0, 0, {
                            'value': 'Other (answer in comment)',
                            'sequence': 5,
                        })],
                }), (0, 0, {
                    'title': 'How many times did you order products on our website?',
                    'sequence': 5,
                    'question_type': 'numerical_box',
                    'constr_mandatory': True,
                }), (0, 0, {
                    'title': 'About our ecommerce',
                    'sequence': 6,
                    'is_page': True,
                    'question_type': False,
                    'description': """<p>This section is about our eCommerce experience itself.</p>""",
                }), (0, 0, {
                    'title': 'Which of the following words would you use to describe our products?',
                    'sequence': 7,
                    'question_type': 'multiple_choice',
                    'constr_mandatory': True,
                    'comments_allowed': True,
                    'comment_count_as_answer': False,
                    'suggested_answer_ids': [
                        (0, 0, {
                            'value': 'High quality',
                            'sequence': 1,
                        }), (0, 0, {
                            'value': 'Useful',
                            'sequence': 2,
                        }), (0, 0, {
                            'value': 'Unique',
                            'sequence': 3,
                        }), (0, 0, {
                            'value': 'Good value for money',
                            'sequence': 4,
                        }), (0, 0, {
                            'value': 'Overpriced',
                            'sequence': 5,
                        }), (0, 0, {
                            'value': 'Impractical',
                            'sequence': 6,
                        }), (0, 0, {
                            'value': 'Ineffective',
                            'sequence': 7,
                        }), (0, 0, {
                            'value': 'Poor quality',
                            'sequence': 8,
                        }), (0, 0, {
                            'value': 'Other',
                            'sequence': 9,
                        })],
                }), (0, 0, {
                    'title': 'What do your think about our new eCommerce?',
                    'sequence': 8,
                    'question_type': 'matrix',
                    'matrix_subtype': 'multiple',
                    'constr_mandatory': True,
                    'suggested_answer_ids': [(0, 0, {
                        'value': 'Totally disagree',
                        'sequence': 1
                    }), (0, 0, {
                        'value': 'Disagree',
                        'sequence': 2,
                    }), (0, 0, {
                        'value': 'Agree',
                        'sequence': 3,
                    }), (0, 0, {
                        'value': 'Totally agree',
                        'sequence': 4,
                    })],
                    'matrix_row_ids': [(0, 0, {
                        'value': 'The new layout and design is fresh and up-to-date',
                        'sequence': 1,
                    }), (0, 0, {
                        'value': 'It is easy to find the product that I want',
                        'sequence': 2,
                    }), (0, 0, {
                        'value': 'The tool to compare the products is useful to make a choice',
                        'sequence': 3,
                    }), (0, 0, {
                        'value': 'The checkout process is clear and secure',
                        'sequence': 4,
                    }), (0, 0, {
                        'value': 'I have added products to my wishlist',
                        'sequence': 5,
                    })],
                }), (0, 0, {
                    'title': 'Do you have any other comments, questions, or concerns?',
                    'sequence': 9,
                    'question_type': 'text_box',
                    'constr_mandatory': False,
                }), (0, 0, {
                    'title': 'How would you rate your experience on our website?',
                    'sequence': 15,
                    'question_type': 'scale',
                    'scale_min': 1,
                    'scale_max': 5,
                    'scale_min_label': 'Bad experience',
                    'scale_mid_label': 'Do the job',
                    'scale_max_label': 'Very good experience',
                    'constr_mandatory': True,
                }),
            ],
        })

    def test_01_admin_survey_tour(self):
        access_token = self.survey_feedback.access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_survey', login="admin")

    def test_02_demo_survey_tour(self):
        access_token = self.survey_feedback.access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_survey', login="demo")

    def test_03_public_survey_tour(self):
        access_token = self.survey_feedback.access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_survey')

    def test_04_public_survey_with_triggers(self):
        """ Check that chained conditional questions are correctly
        hidden from survey when a previously selected triggering answer is
        unselected. E.g., if a specific answer for "Question 1" is selected,
        which triggers asking "Question 2", and a specific answer for
        "Question 2" is selected and triggers asking "Question 3",
        changing the selected answer for "Question 1" should:
          * hide questions 2 and 3
          * enable submitting the survey without answering questions 2 and 3,
           even if "constr_mandatory=True", as they are not visible.
        """
        survey_with_triggers = self.env['survey.survey'].create({
            'title': 'Survey With Triggers',
            'access_token': '3cfadce3-3f7e-41da-920d-10fa0eb19527',
            'access_mode': 'public',
            'users_can_go_back': True,
            'questions_layout': 'one_page',
            'description': "<p>Test survey with conditional questions</p>",
            'question_and_page_ids': [
                (0, 0, {
                    'title': 'Q1',
                    'sequence': 1,
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        Command.create({'value': 'Answer 1'}),
                        Command.create({'value': 'Answer 2'}),
                        Command.create({'value': 'Answer 3'}),
                    ],
                    'constr_mandatory': True,
                }), Command.create({
                    'title': 'Q2',
                    'sequence': 2,
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        Command.create({'value': 'Answer 1'}),
                        Command.create({'value': 'Answer 2'}),
                    ],
                    'constr_mandatory': True,
                }), Command.create({
                    'title': 'Q3',
                    'sequence': 3,
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        Command.create({'value': 'Answer 1'}),
                        Command.create({'value': 'Answer 2'}),
                    ],
                    'constr_mandatory': True,
                }), Command.create({
                    'title': 'Q4',
                    'sequence': 4,
                    'question_type': 'numerical_box',
                    'constr_mandatory': True,
                })
            ]
        })

        q1, q2, q3, q4 = survey_with_triggers.question_and_page_ids
        q1_a1, __, q1_a3 = q1.suggested_answer_ids
        q2_a1 = q2.suggested_answer_ids[0]

        q2.triggering_answer_ids = q1_a1
        q3.triggering_answer_ids = q1_a3 | q2_a1
        q4.triggering_answer_ids = q1_a1

        access_token = survey_with_triggers.access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_survey_chained_conditional_questions')

    def test_05_public_survey_with_trigger_on_different_page(self):
        """Check that conditional questions are shown when triggered from a different page too."""
        survey_with_trigger_on_different_page = self.env['survey.survey'].create({
            'title': 'Survey With Trigger on a different page',
            'access_token': '1cb935bd-2399-4ed1-9e10-c649318fb4dc',
            'access_mode': 'public',
            'users_can_go_back': True,
            'questions_layout': 'page_per_section',
            'description': "<p>Test survey with conditional questions triggered from a previous section</p>",
            'question_and_page_ids': [
                Command.create({
                    'title': 'Section 1',
                    'is_page': True,
                    'sequence': 1,
                    'question_type': False,
                }), Command.create({
                    'title': 'Q1',
                    'sequence': 2,
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        Command.create({'value': 'Answer 1'}),
                        Command.create({'value': 'Answer 2'}),
                        Command.create({'value': 'Answer 3'}),
                    ],
                    'constr_mandatory': False,
                }), Command.create({
                    'title': 'Section 2',
                    'is_page': True,
                    'sequence': 3,
                    'question_type': False,
                }), Command.create({
                    'title': 'Q2',
                    'sequence': 4,
                    'question_type': 'simple_choice',
                    'suggested_answer_ids': [
                        Command.create({'value': 'Answer 1'}),
                        Command.create({'value': 'Answer 2'}),
                    ],
                    'constr_mandatory': False,
                }), Command.create({
                    'title': 'Q3',
                    'sequence': 3,
                    'question_type': 'numerical_box',
                    'constr_mandatory': False,
                }),
            ]
        })

        q1 = survey_with_trigger_on_different_page.question_ids.filtered(lambda q: q.title == 'Q1')
        q1_a1 = q1.suggested_answer_ids.filtered(lambda a: a.value == 'Answer 1')

        q2 = survey_with_trigger_on_different_page.question_ids.filtered(lambda q: q.title == 'Q2')
        q2_a1 = q2.suggested_answer_ids.filtered(lambda a: a.value == 'Answer 1')

        q3 = survey_with_trigger_on_different_page.question_ids.filtered(lambda q: q.title == 'Q3')

        q3.triggering_answer_ids = q1_a1 | q2_a1

        access_token = survey_with_trigger_on_different_page.access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_survey_conditional_question_on_different_page')

    def test_06_survey_prefill(self):
        access_token = self.survey_feedback.access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_survey_prefill')

    def test_07_survey_roaming_mandatory_questions(self):
        survey_with_mandatory_questions = self.env['survey.survey'].create({
            'title': 'Survey With Mandatory questions',
            'access_token': '853ebb30-40f2-43bf-a95a-bbf0e367a365',
            'access_mode': 'public',
            'users_can_go_back': True,
            'questions_layout': 'page_per_question',
            'description': "<p>Test survey with roaming freely option and mandatory questions</p>",
            'question_and_page_ids': [
                Command.create({
                    'title': 'Q1',
                    'sequence': 1,
                    'question_type': 'simple_choice',
                    'constr_mandatory': True,
                    'suggested_answer_ids': [
                        Command.create({'value': 'Answer 1'}),
                        Command.create({'value': 'Answer 2'}),
                        Command.create({'value': 'Answer 3'}),
                    ],
                }), Command.create({
                    'title': 'Q2',
                    'sequence': 2,
                    'question_type': 'simple_choice',
                    'constr_mandatory': True,
                    'suggested_answer_ids': [
                        Command.create({'value': 'Answer 1'}),
                        Command.create({'value': 'Answer 2'}),
                        Command.create({'value': 'Answer 3'}),
                    ],
                }), Command.create({
                    'title': 'Q3',
                    'sequence': 3,
                    'question_type': 'simple_choice',
                    'constr_mandatory': True,
                    'suggested_answer_ids': [
                        Command.create({'value': 'Answer 1'}),
                        Command.create({'value': 'Answer 2'}),
                    ],
                }),
            ]
        })

        access_token = survey_with_mandatory_questions.access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_survey_roaming_mandatory_questions')
