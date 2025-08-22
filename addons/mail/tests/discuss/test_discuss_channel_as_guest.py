# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import tagged
from odoo.addons.base.tests.common import HttpCaseWithUserPortal, HttpCaseWithUserDemo


@tagged("post_install", "-at_install", "is_tour")
class TestMailPublicPage(HttpCaseWithUserPortal, HttpCaseWithUserDemo):
    """Checks that the invite page redirects to the channel and that all
    modules load correctly on the welcome and channel page when authenticated as various users"""

    def setUp(self):
        super().setUp()
        portal_user = mail_new_test_user(
            self.env,
            name='Portal Bowser',
            login='portal_bowser',
            email='portal_bowser@example.com',
            groups='base.group_portal',
        )
        internal_user = mail_new_test_user(
            self.env,
            name='Internal Luigi',
            login='internal_luigi',
            email='internal_luigi@example.com',
            groups='base.group_user',
        )
        guest = self.env['mail.guest'].create({'name': 'Guest Mario'})

        self.channel = self.env['discuss.channel']._create_channel(group_id=None, name='Test channel')
        self.channel.add_members(portal_user.partner_id.ids)
        self.channel.add_members(internal_user.partner_id.ids)
        self.channel.add_members(guest_ids=[guest.id])
        internal_member = self.channel.channel_member_ids.filtered(lambda m: internal_user.partner_id == m.partner_id)
        internal_member._rtc_join_call()

        self.group = self.env['discuss.channel']._create_group(partners_to=(internal_user + portal_user).partner_id.ids, name="Test group")
        self.group.add_members(guest_ids=[guest.id])
        self.tour = "discuss_channel_public_tour.js"

    def _open_channel_page_as_user(self, login):
        self.start_tour(self.channel.invitation_url, self.tour, login=login)
        # Update the body to a unique value to ensure the second run does not confuse the 2 messages.
        self.channel._get_last_messages().body = "a-very-unique-body-in-channel"
        # Second run of the tour as the first call has side effects, like creating user settings or adding members to
        # the channel, so we need to run it again to test different parts of the code.
        self.start_tour(self.channel.invitation_url, self.tour, login=login)

    def _open_group_page_as_user(self, login):
        self.start_tour(self.group.invitation_url, self.tour, login=login)
        # Update the body to a unique value to ensure the second run does not confuse the 2 messages.
        self.channel._get_last_messages().body = "a-very-unique-body-in-group"
        # Second run of the tour as the first call has side effects, like creating user settings or adding members to
        # the channel, so we need to run it again to test different parts of the code.
        self.start_tour(self.group.invitation_url, self.tour, login=login)

    def test_discuss_channel_public_page_as_admin(self):
        self._open_channel_page_as_user('admin')

    def test_mail_group_public_page_as_admin(self):
        self._open_group_page_as_user('admin')

    def test_discuss_channel_public_page_as_guest(self):
        self.start_tour(self.channel.invitation_url, "discuss_channel_as_guest_tour.js")
        guest = self.env['mail.guest'].search([('channel_ids', 'in', self.channel.id)], limit=1, order='id desc')
        self.assertIn("joined the channel", self.channel.message_ids[0].body)
        self.assertTrue(self.channel.message_ids[0].author_guest_id)
        self.start_tour(self.channel.invitation_url, self.tour, cookies={guest._cookie_name: guest._format_auth_cookie()})

    def test_discuss_channel_public_page_call_public(self):
        self.channel.default_display_mode = 'video_full_screen'
        self.start_tour(self.channel.invitation_url, "discuss_channel_call_public_tour.js")

    def test_mail_group_public_page_as_guest(self):
        self.start_tour(self.group.invitation_url, "discuss_channel_as_guest_tour.js")
        guest = self.env['mail.guest'].search([('channel_ids', 'in', self.channel.id)], limit=1, order='id desc')
        self.start_tour(self.group.invitation_url, self.tour, cookies={guest._cookie_name: guest._format_auth_cookie()})

    def test_discuss_channel_public_page_as_internal(self):
        self._open_channel_page_as_user('demo')

    def test_mail_group_public_page_as_internal(self):
        self._open_group_page_as_user('demo')

    def test_discuss_channel_public_page_as_portal(self):
        self._open_channel_page_as_user('portal')

    def test_mail_group_public_page_as_portal(self):
        self._open_group_page_as_user('portal')

    def test_chat_from_token_as_guest(self):
        self.env['ir.config_parameter'].set_param('mail.chat_from_token', True)
        self.url_open('/chat/xyz')
        channel = self.env['discuss.channel'].search([('uuid', '=', 'xyz')])
        self.assertEqual(len(channel), 1)

    def test_channel_invitation_from_token(self):
        public_channel = self.env["discuss.channel"]._create_channel(name="Public Channel", group_id=None)
        internal_channel = self.env["discuss.channel"]._create_channel(name="Internal Channel", group_id=self.env.ref("base.group_user").id)

        public_response = self.url_open(public_channel.invitation_url)
        self.assertEqual(public_response.status_code, 200)

        internal_response = self.url_open(internal_channel.invitation_url)
        self.assertEqual(internal_response.status_code, 404)

    def test_sidebar_in_public_page(self):
        guest = self.env['mail.guest'].create({'name': 'Guest'})
        channel_1 = self.env["discuss.channel"]._create_channel(name="Channel 1", group_id=None)
        channel_2 = self.env["discuss.channel"]._create_channel(name="Channel 2", group_id=None)
        channel_1.add_members(guest_ids=[guest.id])
        channel_2.add_members(guest_ids=[guest.id])
        self.start_tour(f"/discuss/channel/{channel_1.id}", "sidebar_in_public_page_tour", cookies={guest._cookie_name: guest._format_auth_cookie()})
