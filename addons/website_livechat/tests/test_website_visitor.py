# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from odoo.addons.website.tests.test_website_visitor import WebsiteVisitorTestsCommon


@tagged('website_visitor')
class WebsiteVisitorTestsLivechat(WebsiteVisitorTestsCommon):

    def test_link_to_visitor_livechat(self):
        """ Same as parent's 'test_link_to_visitor' except we also test that conversations
        are merged into main visitor. """
        [main_visitor, linked_visitor] = self.env['website.visitor'].create([
            self._prepare_main_visitor_data(),
            self._prepare_linked_visitor_data()
        ])
        all_discuss_channels = (main_visitor + linked_visitor).discuss_channel_ids
        linked_visitor._merge_visitor(main_visitor)

        self.assertVisitorDeactivated(linked_visitor, main_visitor)

        # conversations of both visitors should be merged into main one
        self.assertEqual(len(main_visitor.discuss_channel_ids), 2)
        self.assertEqual(main_visitor.discuss_channel_ids, all_discuss_channels)

    def _prepare_main_visitor_data(self):
        values = super()._prepare_main_visitor_data()
        test_partner = self.env['res.partner'].create({'name': 'John Doe'})
        values.update(
            {
                "partner_id": test_partner.id,
                "discuss_channel_ids": [
                    Command.create({"name": "Conversation 1", "livechat_end_dt": fields.Datetime.now()}),
                ],
            }
        )
        return values

    def _prepare_linked_visitor_data(self):
        values = super()._prepare_linked_visitor_data()
        values.update(
            {
                "discuss_channel_ids": [
                    Command.create({"name": "Conversation 2", "livechat_end_dt": fields.Datetime.now()}),
                ],
            }
        )
        return values

    def test_visitor_page_statistics_access(self):
        operator = new_test_user(self.env, "operator", groups="im_livechat.im_livechat_group_user")
        visitor = self._get_last_visitor()
        visitor.with_user(operator).page_count
        with self.assertRaises(AccessError):
            visitor.with_user(operator).page_ids

    def test_new_visitor_linked_to_guest_livechats(self):
        operator = self.user_admin
        livechat_channel = self.env["im_livechat.channel"].create({
            "name": "Awesome Channel",
            "user_ids": [Command.set([operator.id])],
        })
        self.env["mail.presence"]._update_presence(operator)
        existing_visitor = self.env["website.visitor"].create({
            "access_token": self.partner_admin_duplicate.id,
            "website_id": self.website.id,
        })
        existing_channel_id = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": livechat_channel.id},
        )["channel_id"]
        existing_channel = self.env["discuss.channel"].browse(existing_channel_id)
        existing_channel.livechat_visitor_id = existing_visitor
        new_channel_id = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": livechat_channel.id},
        )["channel_id"]
        new_channel = self.env["discuss.channel"].browse(new_channel_id)
        self.assertFalse(new_channel.livechat_visitor_id)
        self.make_jsonrpc_request(
            route="/website/odoo_track",
            params={
                "res_model": self.tracked_page._name,
                "res_id": self.tracked_page.id,
            },
        )
        new_visitor = self._get_last_visitor()
        self.assertNotEqual(new_visitor, existing_visitor)
        self.assertEqual(existing_channel.livechat_visitor_id, existing_visitor)
        self.assertEqual(new_channel.livechat_visitor_id, new_visitor)

    def test_tracking_does_not_logout_authenticated_user_with_guest_cookie(self):
        operator = self.user_admin
        livechat_channel = self.env["im_livechat.channel"].create({
            "name": "Awesome Channel",
            "user_ids": [Command.set([operator.id])],
        })
        self.env["mail.presence"]._update_presence(operator)

        self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "channel_id": livechat_channel.id,
            },
        )
        self.assertIn(self.env["mail.guest"]._cookie_name, self.opener.cookies)

        self._authenticate_via_web(self.user_admin.login, "admin")
        self.assertEqual(
            self.make_jsonrpc_request("/web/session/get_session_info")["uid"],
            self.user_admin.id,
        )

        self.make_jsonrpc_request(
            route="/website/odoo_track",
            params={
                "res_model": self.tracked_page._name,
                "res_id": self.tracked_page.id,
            },
        )

        self.assertEqual(
            self.make_jsonrpc_request("/web/session/get_session_info")["uid"],
            self.user_admin.id,
        )
