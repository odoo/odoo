# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo.fields import Datetime
from odoo import tests
from odoo.tests.common import users
from odoo.addons.website_slides.tests.test_ui_wslides import TestUICommon


@tests.common.tagged('post_install', '-at_install')
class TestUi(TestUICommon):

    def setUp(cls):
        super().setUp()

        # =====================
        # CERTIFICATION SURVEY
        # =====================

        cls.furniture_survey = cls.env['survey.survey'].create({
            'title': 'Furniture Creation Certification',
            'access_token': '5632a4d7-48cf-aaaa-8c52-2174d58cf50b',
            'access_mode': 'public',
            'questions_layout': 'one_page',
            'users_can_go_back': True,
            'users_login_required': True,
            'scoring_type': 'scoring_with_answers',
            'certification': True,
            'certification_mail_template_id': cls.env.ref('survey.mail_template_certification').id,
            'is_attempts_limited': True,
            'attempts_limit': 3,
            'description': "<p>Test your furniture knowledge!</p>",
            'question_and_page_ids': [
                (0, 0, {
                    'title': 'Furniture',
                    'sequence': 1,
                    'is_page': True,
                    'question_type': False,
                    'description': "&lt;p&gt;Test your furniture knowledge!&lt;/p&gt",
                }), (0, 0, {
                    'title': 'What type of wood is the best for furniture?',
                    'sequence': 2,
                    'question_type': 'simple_choice',
                    'constr_mandatory': True,
                    'suggested_answer_ids': [
                        (0, 0, {
                            'value': 'Fir',
                            'sequence': 1,
                        }), (0, 0, {
                            'value': 'Oak',
                            'sequence': 2,
                            'is_correct': True,
                            'answer_score': 2.0,
                        }), (0, 0, {
                            'value': 'Ash',
                            'sequence': 3,
                        }), (0, 0, {
                            'value': 'Beech',
                            'sequence': 4,
                        })
                    ]
                }), (0, 0, {
                    'title': 'Select all the furniture shown in the video',
                    'sequence': 3,
                    'question_type': 'multiple_choice',
                    'suggested_answer_ids': [
                        (0, 0, {
                            'value': 'Chair',
                            'sequence': 1,
                            'is_correct': True,
                            'answer_score': 1.0,
                        }), (0, 0, {
                            'value': 'Table',
                            'sequence': 2,
                            'answer_score': -1.0,
                        }), (0, 0, {
                            'value': 'Desk',
                            'sequence': 3,
                            'is_correct': True,
                            'answer_score': 1.0,
                        }), (0, 0, {
                            'value': 'Shelve',
                            'sequence': 4,
                            'is_correct': True,
                            'answer_score': 1.0,
                        }), (0, 0, {
                            'value': 'Bed',
                            'sequence': 5,
                            'answer_score': -1.0,
                        })
                    ]
                }), (0, 0, {
                    'title': 'What do you think about the content of the course? (not rated)',
                    'sequence': 4,
                    'question_type': 'text_box',
                })
            ]
        })

        # ===============
        # COURSE PRODUCT
        # ===============
        cls.furniture_course_product = cls.env['product.product'].create({
            'name': 'DIY Furniture Course',
            'list_price': 100.0,
            'type': 'service',
            'is_published': True,
        })

        # ===============
        # COURSE CHANNEL
        # ===============
        cls.furniture_course = cls.env['slide.channel'].create({
            'name': 'DIY Furniture - TEST',
            'user_id': cls.env.ref('base.user_admin').id,
            'enroll': 'payment',
            'product_id': cls.furniture_course_product.id,
            'channel_type': 'training',
            'allow_comment': True,
            'promote_strategy': 'most_voted',
            'is_published': True,
            'description': 'So much amazing certification.',
            'create_date': Datetime.now() - relativedelta(days=2),
            'slide_ids': [
                (0, 0, {
                    'name': 'DIY Furniture Certification',
                    'sequence': 1,
                    'slide_category': 'certification',
                    'category_id': False,
                    'is_published': True,
                    'is_preview': False,
                    'description': "It's time to test your knowledge!",
                    'survey_id': cls.furniture_survey.id,
                })
            ]
        })

    @users("portal")
    def test_course_certification_employee(self):
        # use proper environment to test user dependent computes
        self.furniture_course = self.env['slide.channel'].browse(self.furniture_course.id)

        user_portal = self.env.user
        sale_order_data = {
            'partner_id': user_portal.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.furniture_course_product.name,
                    'product_id': self.furniture_course_product.id,
                    'product_uom_qty': 1,
                    'price_unit': self.furniture_course_product.list_price,
                })
            ]}

        # =================
        # FAILURE ATTEMPTS
        # =================
        self.env['sale.order'].sudo().create(sale_order_data).action_confirm()
        # Member should have access to the course
        self.assertTrue(self.furniture_course.is_member)
        self.start_tour('/slides', 'certification_member_failure', login=user_portal.login)
        # Member should no longer have access to the course
        self.assertFalse(self.furniture_course.is_member)

        # ===================
        # SUCCESSFUL ATTEMPT
        # ===================
        self.env['sale.order'].sudo().create(sale_order_data).action_confirm()
        # Member regains access to the course
        self.assertTrue(self.furniture_course.is_member)

        self.start_tour('/slides', 'certification_member_success', login=user_portal.login)

        # ============
        # EXTRA TESTS
        # ============
        member = self.env['slide.channel.partner'].sudo().search([
            ('channel_id', '=', self.furniture_course.id),
            ('partner_id', '=', user_portal.partner_id.id),
        ])
        self.assertTrue(member)
        self.assertEqual(member.member_status, 'completed', "Member status should be 'completed'")
        self.assertEqual(member.completion, 100, "Completion rate should be 100%")
