# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUiCertification(HttpCaseWithUserDemo):

    def setUp(self):
        super(TestUiCertification, self).setUp()

        self.survey_certification = self.env['survey.survey'].create({
            'title': 'MyCompany Vendor Certification',
            'access_token': '4ead4bc8-b8f2-4760-a682-1fde8daaaaac',
            'access_mode': 'public',
            'questions_layout': 'one_page',
            'users_can_go_back': True,
            'users_login_required': True,
            'scoring_type': 'scoring_with_answers',
            'certification': True,
            'certification_mail_template_id': self.env.ref('survey.mail_template_certification').id,
            'is_time_limited': 'limited',
            'time_limit': 10.0,
            'is_attempts_limited': True,
            'attempts_limit': 2,
            'description': """&lt;p&gt;Test your vendor skills!.&lt;/p&gt;""",
            'question_and_page_ids': [
                (0, 0, {
                    'title': 'Products',
                    'sequence': 1,
                    'is_page': True,
                    'question_type': False,
                    'description': '&lt;p&gt;Test your knowledge of your products!&lt;/p&gt;',
                }), (0, 0, {
                    'title': 'Do we sell Acoustic Bloc Screens?',
                    'sequence': 2,
                    'question_type': 'simple_choice',
                    'constr_mandatory': True,
                    'suggested_answer_ids': [
                        (0, 0, {
                            'value': 'No',
                            'sequence': 1,
                        }), (0, 0, {
                            'value': 'Yes',
                            'sequence': 2,
                            'is_correct': True,
                            'answer_score': 2,
                        })
                    ],
                }), (0, 0, {
                    'title': 'Select all the existing products',
                    'sequence': 3,
                    'question_type': 'multiple_choice',
                    'suggested_answer_ids': [
                        (0, 0, {
                            'value': 'Chair floor protection',
                            'sequence': 1,
                            'is_correct': True,
                            'answer_score': 1,
                        }), (0, 0, {
                            'value': 'Fanta',
                            'sequence': 2,
                            'answer_score': -1,
                        }), (0, 0, {
                            'value': 'Conference chair',
                            'sequence': 3,
                            'is_correct': True,
                            'answer_score': 1,
                        }), (0, 0, {
                            'value': 'Drawer',
                            'sequence': 4,
                            'is_correct': True,
                            'answer_score': 1,
                        }), (0, 0, {
                            'value': 'Customizable Lamp',
                            'sequence': 5,
                            'answer_score': -1,
                        })
                    ]
                }), (0, 0, {
                    'title': 'Select all the available customizations for our Customizable Desk',
                    'sequence': 4,
                    'question_type': 'multiple_choice',
                    'suggested_answer_ids': [
                        (0, 0, {
                            'value': 'Color',
                            'sequence': 1,
                            'is_correct': True,
                            'answer_score': 1,
                        }), (0, 0, {
                            'value': 'Height',
                            'sequence': 2,
                            'answer_score': -1,
                        }), (0, 0, {
                            'value': 'Width',
                            'sequence': 3,
                            'is_correct': True,
                            'answer_score': 1,
                        }), (0, 0, {
                            'value': 'Legs',
                            'sequence': 4,
                            'is_correct': True,
                            'answer_score': 1,
                        }), (0, 0, {
                            'value': 'Number of drawers',
                            'sequence': 5,
                            'answer_score': -1,
                        })
                    ]
                }), (0, 0, {
                    'title': 'How many versions of the Corner Desk do we have?',
                    'sequence': 5,
                    'question_type': 'simple_choice',
                    'constr_mandatory': True,
                    'suggested_answer_ids': [
                        (0, 0, {
                            'value': 1,
                            'sequence': 1,
                        }), (0, 0, {
                            'value': 2,
                            'sequence': 2,
                            'is_correct': True,
                            'answer_score': 2,
                        }), (0, 0, {
                            'value': 3,
                            'sequence': 3,
                        }), (0, 0, {
                            'value': 4,
                            'sequence': 4,
                        })
                    ]
                }), (0, 0, {
                    'title': 'Do you think we have missing products in our catalog? (not rated)',
                    'sequence': 6,
                    'question_type': 'text_box',
                }), (0, 0, {
                    'title': 'Prices',
                    'sequence': 7,
                    'is_page': True,
                    'question_type': False,
                    'description': """&lt;p&gt;Test your knowledge of our prices.&lt;/p&gt;""",
                }), (0, 0, {
                    'title': 'How much do we sell our Cable Management Box?',
                    'sequence': 8,
                    'question_type': 'simple_choice',
                    'constr_mandatory': True,
                    'suggested_answer_ids': [
                        (0, 0, {
                            'value': '$20',
                            'sequence': 1,
                        }), (0, 0, {
                            'value': '$50',
                            'sequence': 2,
                        }), (0, 0, {
                            'value': '$80',
                            'sequence': 3,
                        }), (0, 0, {
                            'value': '$100',
                            'sequence': 4,
                            'is_correct': True,
                            'answer_score': 2,
                        }), (0, 0, {
                            'value': '$200',
                            'sequence': 5,
                        }), (0, 0, {
                            'value': '$300',
                            'sequence': 6,
                        })
                    ]
                }), (0, 0, {
                    'title': 'Select all the products that sell for $100 or more',
                    'sequence': 9,
                    'question_type': 'multiple_choice',
                    'suggested_answer_ids': [
                        (0, 0, {
                            'value': 'Corner Desk Right Sit',
                            'sequence': 1,
                            'answer_score': 1,
                            'is_correct': True,
                        }), (0, 0, {
                            'value': 'Desk Combination',
                            'sequence': 2,
                            'answer_score': 1,
                            'is_correct': True,
                        }), (0, 0, {
                            'value': 'Cabinet with Doors',
                            'sequence': 3,
                            'answer_score': -1,
                        }), (0, 0, {
                            'value': 'Large Desk',
                            'sequence': 4,
                            'answer_score': 1,
                            'is_correct': True,
                        }), (0, 0, {
                            'value': 'Letter Tray',
                            'sequence': 5,
                            'answer_score': -1,
                        }), (0, 0, {
                            'value': 'Office Chair Black',
                            'sequence': 6,
                            'answer_score': -1,
                        }),
                    ]
                }), (0, 0, {
                    'title': 'What do you think about our prices (not rated)?',
                    'sequence': 10,
                    'question_type': 'simple_choice',
                    'constr_mandatory': True,
                    'suggested_answer_ids': [
                        (0, 0, {
                            'value': 'Very underpriced',
                            'sequence': 1,
                        }), (0, 0, {
                            'value': 'Underpriced',
                            'sequence': 2,
                        }), (0, 0, {
                            'value': 'Correctly priced',
                            'sequence': 3,
                        }), (0, 0, {
                            'value': 'A little bit overpriced',
                            'sequence': 4,
                        }), (0, 0, {
                            'value': 'A lot overpriced',
                            'sequence': 5,
                        })
                    ]
                }), (0, 0, {
                    'title': 'Policies',
                    'sequence': 11,
                    'is_page': True,
                    'question_type': False,
                    'description': """&lt;p&gt;Test your knowledge of our policies.&lt;/p&gt;""",
                }), (0, 0, {
                    'title': 'How many days is our money-back guarantee?',
                    'sequence': 12,
                    'question_type': 'numerical_box',
                    'constr_mandatory': True,
                    'is_scored_question': True,
                    'answer_numerical_box': 30,
                    'answer_score': 1,
                }), (0, 0, {
                    'title': 'If a customer purchases a product on 6 January 2020, what is the latest day we expect to ship it?',
                    'sequence': 13,
                    'question_type': 'date',
                    'is_scored_question': True,
                    'answer_date': '2020-01-08',
                    'answer_score': 1,
                }), (0, 0, {
                    'title': 'If a customer purchases a 1 year warranty on 6 January 2020, when do we expect the warranty to expire?',
                    'sequence': 14,
                    'question_type': 'datetime',
                    'is_scored_question': True,
                    'answer_datetime': '2021-01-07 00:00:01',
                    'answer_score': 1,
                }), (0, 0, {
                    'title': 'What day to you think is best for us to start having an annual sale (not rated)?',
                    'sequence': 15,
                    'question_type': 'date',
                }), (0, 0, {
                    'title': 'What day and time do you think most customers are most likely to call customer service (not rated)?',
                    'sequence': 16,
                    'question_type': 'datetime',
                }), (0, 0, {
                    'title': 'How many chairs do you think we should aim to sell in a year (not rated)?',
                    'sequence': 17,
                    'question_type': 'numerical_box',
                })
            ]
        })

    def test_04_certification_success_tour(self):
        access_token = self.survey_certification.access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_certification_success', login="demo")

    def test_05_certification_failure_tour(self):
        access_token = self.survey_certification.access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_certification_failure', login="demo")
