# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from dateutil.relativedelta import relativedelta
from odoo import tests
from odoo.fields import Datetime
from odoo.tools import mute_logger
from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.tools.misc import file_open


class TestUICommon(HttpCaseWithUserDemo, HttpCaseWithUserPortal):

    def setUp(self):
        super(TestUICommon, self).setUp()
        # Load pdf and img contents
        pdf_content = base64.b64encode(file_open('website_slides/static/src/img/presentation.pdf', "rb").read())
        img_content = base64.b64encode(file_open('website_slides/static/src/img/slide_demo_gardening_1.jpg', "rb").read())

        self.channel = self.env['slide.channel'].create({
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
                    'binary_content': pdf_content,
                    'slide_category': 'document',
                    'is_published': True,
                    'is_preview': True,
                }), (0, 0, {
                    'name': 'Home Gardening',
                    'sequence': 2,
                    'image_1920': img_content,
                    'slide_category': 'infographic',
                    'is_published': True,
                }), (0, 0, {
                    'name': 'Mighty Carrots',
                    'sequence': 3,
                    'image_1920': img_content,
                    'slide_category': 'infographic',
                    'is_published': True,
                }), (0, 0, {
                    'name': 'How to Grow and Harvest The Best Strawberries | Basics',
                    'sequence': 4,
                    'binary_content': pdf_content,
                    'slide_category': 'document',
                    'is_published': True,
                }), (0, 0, {
                    'name': 'Test your knowledge',
                    'sequence': 5,
                    'slide_category': 'quiz',
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

    @mute_logger("odoo.http", "odoo.addons.base.models.ir_rule", "werkzeug")
    def test_course_access_fail_redirection(self):
        """Test that the user is redirected to /slides with en error displayed instead of the standard error page."""
        self.channel.visibility = "members"
        urls = (
            f"/slides/aaa-{self.channel.id}",
            f"/slides/{self.channel.id}",
            f"/slides/{self.channel.id}/page/1",
            f"/slides/aaa-{self.channel.id}/page/1",
            f"/slides/slide/{self.channel.slide_ids[0].id}",
            f"/slides/slide/aaa-{self.channel.slide_ids[0].id}",
            f"/slides/slide/{self.channel.slide_ids[0].id}/pdf_content",
            f"/slides/slide/aaa-{self.channel.slide_ids[0].id}/pdf_content",
        )
        for url in urls:
            response = self.url_open(url, allow_redirects=False)
            self.assertTrue(response.headers.get("Location", "").endswith("/slides?invite_error=no_rights"))

        # auth="user" has priority
        urls = (
            f"/slides/slide/aaa-{self.channel.slide_ids[0].id}/set_completed",
            f"/slides/slide/{self.channel.slide_ids[0].id}/set_completed",
        )
        for url in urls:
            response = self.url_open(url, allow_redirects=False)
            self.assertIn("/web/login", response.headers.get("Location", ""))

    def test_course_member_employee(self):
        user_demo = self.user_demo
        user_demo.write({
            'karma': 1,
            'groups_id': [(6, 0, self.env.ref('base.group_user').ids)]
        })

        self.start_tour('/slides', 'course_member', login=user_demo.login)

    def test_course_member_elearning_officer(self):
        user_demo = self.user_demo
        user_demo.write({
            'karma': 1,
            'groups_id': [(6, 0, (self.env.ref('base.group_user') | self.env.ref('website_slides.group_website_slides_officer')).ids)]
        })

        self.start_tour('/slides', 'course_member', login=user_demo.login)

    def test_course_member_portal(self):
        user_portal = self.user_portal
        user_portal.karma = 1

        self.start_tour('/slides', 'course_member', login=user_portal.login)

    def test_full_screen_edition_website_restricted_editor(self):
        # group_website_designer
        user_demo = self.env.ref('base.user_demo')
        user_demo.write({
            'groups_id': [(5, 0), (4, self.env.ref('base.group_user').id), (4, self.env.ref('website.group_website_restricted_editor').id)]
        })

        self.start_tour(self.env['website'].get_client_action_url('/slides'), 'full_screen_web_editor', login=user_demo.login)

    def test_course_reviews_elearning_officer(self):
        user_demo = self.user_demo
        user_demo.write({
            'groups_id': [(6, 0, (self.env.ref('base.group_user') | self.env.ref('website_slides.group_website_slides_officer')).ids)]
        })

        # The user must be a course member before being able to post a log note.
        self.channel._action_add_members(user_demo.partner_id)
        self.channel.with_user(user_demo).message_post(
            body='Log note', subtype_xmlid='mail.mt_note', message_type='comment')

        self.start_tour('/slides', 'course_reviews', login=user_demo.login)


@tests.common.tagged('post_install', '-at_install')
class TestUiPublisher(HttpCaseWithUserDemo):

    def test_course_publisher_elearning_manager(self):
        user_demo = self.user_demo
        user_demo.write({
            'groups_id': [
                (5, 0),
                (4, self.env.ref('base.group_user').id),
                (4, self.env.ref('website_slides.group_website_slides_manager').id)
            ],
        })

        self.start_tour(self.env['website'].get_client_action_url('/slides'), 'course_publisher_standard', login=user_demo.login)


@tests.common.tagged('post_install', '-at_install')
class TestUiMemberInvited(TestUICommon):

    def setUp(self):
        super(TestUiMemberInvited, self).setUp()
        self.channel_partner_portal = self.env['slide.channel.partner'].create({
            'channel_id': self.channel.id,
            'partner_id': self.user_portal.partner_id.id,
            'member_status': 'invited',
            'last_invitation_date': Datetime.now(),
        })
        self.portal_invite_url = self.channel_partner_portal.invitation_link

    def test_invite_check_channel_preview_as_logged_connected_on_invite(self):
        self.channel.enroll = 'invite'
        self.channel.visibility = 'connected'
        self.start_tour(self.portal_invite_url, 'invite_check_channel_preview_as_logged', login='portal')

    def test_invite_check_channel_preview_as_public_connected_on_invite(self):
        self.channel.enroll = 'invite'
        self.channel.visibility = 'connected'
        self.start_tour(self.portal_invite_url, 'invite_check_channel_preview_as_public', login=None)

    def test_invite_check_channel_preview_as_logged_members(self):
        self.channel.visibility = 'members'
        self.start_tour(self.portal_invite_url, 'invite_check_channel_preview_as_logged', login='portal')

    def test_invite_check_channel_preview_as_public_members(self):
        self.channel.visibility = 'members'
        self.start_tour(self.portal_invite_url, 'invite_check_channel_preview_as_public', login=None)

    def test_invite_check_channel_preview_as_logged_public(self):
        self.start_tour(self.portal_invite_url, 'invite_check_channel_preview_as_logged', login='portal')

    def test_invite_check_channel_preview_as_public_public(self):
        self.start_tour(self.portal_invite_url, 'invite_check_channel_preview_as_public', login=None)


@tests.common.tagged('external', 'post_install', '-standard', '-at_install')
class TestUiPublisherYoutube(HttpCaseWithUserDemo):

    def test_course_member_yt_employee(self):
        # remove membership because we need to be able to join the course during the tour
        user_demo = self.user_demo
        user_demo.write({
            'groups_id': [(5, 0), (4, self.env.ref('base.group_user').id)]
        })
        self.env.ref('website_slides.slide_channel_demo_3_furn0')._remove_membership(self.env.ref('base.partner_demo').ids)

        self.start_tour('/slides', 'course_member_youtube', login=user_demo.login)

    def test_course_publisher_elearning_manager(self):
        user_demo = self.user_demo
        user_demo.write({
            'groups_id': [(5, 0), (4, self.env.ref('base.group_user').id), (4, self.env.ref('website_slides.group_website_slides_manager').id)]
        })

        self.start_tour(self.env['website'].get_client_action_url('/slides'), 'course_publisher', login=user_demo.login)
