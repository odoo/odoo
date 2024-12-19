# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import HttpCase, tagged
from odoo.addons.mail.tests.common import MailCommon


@tagged("post_install", "-at_install", "discuss_action")
class TestDiscussAction(HttpCase, MailCommon):
    def test_go_back_to_thread_from_breadcrumbs(self):
        self.start_tour(
            "/odoo/discuss?active_id=mail.box_inbox",
            "discuss_go_back_to_thread_from_breadcrumbs.js",
            login="admin",
        )

    def test_join_call_with_client_action(self):
        inviting_user = self.env['res.users'].sudo().create({'name': "Inviting User", 'login': 'inviting'})
        invited_user = self.env['res.users'].sudo().create({'name': "Invited User", 'login': 'invited'})
        channel = self.env['discuss.channel'].with_user(inviting_user)._get_or_create_chat(partners_to=invited_user.partner_id.ids)
        channel_member = channel.sudo().channel_member_ids.filtered(
            lambda channel_member: channel_member.partner_id == inviting_user.partner_id)
        self._reset_bus()
        channel_member._rtc_join_call()
        self.start_tour(
            f"/odoo/{channel.id}/action-mail.action_discuss?call=accept",
            "discuss_channel_call_action.js",
            login=invited_user.login,
        )
