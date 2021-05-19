# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from dateutil.relativedelta import relativedelta
from odoo import tests
from odoo.fields import Datetime
from odoo.modules.module import get_module_resource
from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal


class TestUICommon(HttpCaseWithUserDemo, HttpCaseWithUserPortal):
    
    def setUp(self):
        super(TestUICommon, self).setUp()
        # Load pdf and img contents
        pdf_path = get_module_resource('website_slides', 'static', 'src', 'img', 'presentation.pdf')
        pdf_content = base64.b64encode(open(pdf_path, "rb").read())
        img_path = get_module_resource('website_slides', 'static', 'src', 'img', 'slide_demo_gardening_1.jpg')
        img_content = base64.b64encode(open(img_path, "rb").read())

        self.env['slide.channel'].create({
            'name': 'Basics of Gardening - Test',
            'user_id': self.env.ref('base.user_admin').id,
            'enroll': 'public',
            'channel_type': 'training',
            'allow_comment': True,
            'promote_strategy': 'most_voted',
            'is_published': True,
            'description': 'Learn the basics of gardening !',
            'create_date': Datetime.now() - relativedelta(days=8),
            'slide_ids': [
                (0, 0, {
                    'name': 'Gardening: The Know-How',
                    'sequence': 1,
                    'datas': pdf_content,
                    'slide_type': 'presentation',
                    'is_published': True,
                    'is_preview': True,
                }), (0, 0, {
                    'name': 'Home Gardening',
                    'sequence': 2,
                    'image_1920': img_content,
                    'slide_type': 'infographic',
                    'is_published': True,
                }), (0, 0, {
                    'name': 'Mighty Carrots',
                    'sequence': 3,
                    'image_1920': img_content,
                    'slide_type': 'infographic',
                    'is_published': True,
                }), (0, 0, {
                    'name': 'How to Grow and Harvest The Best Strawberries | Basics',
                    'sequence': 4,
                    'datas': pdf_content,
                    'slide_type': 'document',
                    'is_published': True,
                }), (0, 0, {
                    'name': 'Test your knowledge',
                    'sequence': 5,
                    'slide_type': 'quiz',
                    'is_published': True,
                    'question_ids': [
                        (0, 0, {
                            'question': 'What is a strawberry ?',
                            'answer_ids': [
                                (0, 0, {
                                    'text_value': 'A fruit',
                                    'is_correct': True,
                                    'sequence': 1,
                                }), (0, 0, {
                                    'text_value': 'A vegetable',
                                    'sequence': 2,
                                }), (0, 0, {
                                    'text_value': 'A table',
                                    'sequence': 3,
                                })
                            ]
                        }), (0, 0, {
                            'question': 'What is the best tool to dig a hole for your plants ?',
                            'answer_ids': [
                                (0, 0, {
                                    'text_value': 'A shovel',
                                    'is_correct': True,
                                    'sequence': 1,
                                }), (0, 0, {
                                    'text_value': 'A spoon',
                                    'sequence': 2,
                                })
                            ]
                        })
                    ]
                })
            ]
        })


@tests.common.tagged('post_install', '-at_install')
class TestUi(TestUICommon):

    def test_course_member_employee(self):
        user_demo = self.user_demo
        user_demo.flush()
        user_demo.write({
            'groups_id': [(5, 0), (4, self.env.ref('base.group_user').id)]
        })

        self.browser_js(
            '/slides',
            'odoo.__DEBUG__.services["web_tour.tour"].run("course_member")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.course_member.ready',
            login=user_demo.login)

    def test_course_member_elearning_officer(self):
        user_demo = self.user_demo
        user_demo.flush()
        user_demo.write({
            'groups_id': [(5, 0), (4, self.env.ref('base.group_user').id), (4, self.env.ref('website_slides.group_website_slides_officer').id)]
        })

        self.browser_js(
            '/slides',
            'odoo.__DEBUG__.services["web_tour.tour"].run("course_member")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.course_member.ready',
            login=user_demo.login)

    def test_course_member_portal(self):
        user_portal = self.user_portal
        user_portal.flush()

        self.browser_js(
            '/slides',
            'odoo.__DEBUG__.services["web_tour.tour"].run("course_member")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.course_member.ready',
            login=user_portal.login)

    def test_full_screen_edition_website_publisher(self):
        # group_website_designer
        user_demo = self.env.ref('base.user_demo')
        user_demo.flush()
        user_demo.write({
            'groups_id': [(5, 0), (4, self.env.ref('base.group_user').id), (4, self.env.ref('website.group_website_publisher').id)]
        })

        self.browser_js(
            '/slides',
            'odoo.__DEBUG__.services["web_tour.tour"].run("full_screen_web_editor")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.full_screen_web_editor.ready',
            login=user_demo.login)


@tests.common.tagged('external', 'post_install', '-standard', '-at_install')
class TestUiYoutube(HttpCaseWithUserDemo):

    def test_course_member_yt_employee(self):
        # remove membership because we need to be able to join the course during the tour
        user_demo = self.user_demo
        user_demo.flush()
        user_demo.write({
            'groups_id': [(5, 0), (4, self.env.ref('base.group_user').id)]
        })
        self.env.ref('website_slides.slide_channel_demo_3_furn0')._remove_membership(self.env.ref('base.partner_demo').ids)

        self.browser_js(
            '/slides',
            'odoo.__DEBUG__.services["web_tour.tour"].run("course_member_youtube")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.course_member_youtube.ready',
            login=user_demo.login)

    def test_course_publisher_elearning_manager(self):
        user_demo = self.user_demo
        user_demo.flush()
        user_demo.write({
            'groups_id': [(5, 0), (4, self.env.ref('base.group_user').id), (4, self.env.ref('website_slides.group_website_slides_manager').id)]
        })

        self.browser_js(
            '/slides',
            'odoo.__DEBUG__.services["web_tour.tour"].run("course_publisher")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.course_publisher.ready',
            login=user_demo.login)
