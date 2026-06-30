# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, fields
from odoo.addons.website.tests.test_website_visitor import WebsiteVisitorTestsCommon
from odoo.tests import new_test_user, tagged
from odoo.exceptions import AccessError


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

    def test_visitor_id_continuity_across_sessions(self):
        self.set_registry_readonly_mode(False)  # Allow creation of visitors

        operator = self.user_admin
        livechat_channel = self.env["im_livechat.channel"].create({
            "name": "Awesome Channel",
            "user_ids": [Command.set([operator.id])],
        })
        self.env["mail.presence"]._update_presence(operator)

        # Anonymous user
        self.url_open(self.tracked_page.url)  # visitor created
        res_1 = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "channel_id": livechat_channel.id,
            },
        )
        channel_1 = self.env["discuss.channel"].browse(res_1["channel_id"])
        visitor_1 = self._get_last_visitor()
        self.assertEqual(channel_1.livechat_visitor_id, visitor_1)
        channel_1._close_livechat_session()

        # After login, the same visitor record is retained
        self._authenticate_via_web(self.user_portal.login, "portal")
        res_2 = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "channel_id": livechat_channel.id,
            },
        )
        channel_2 = self.env["discuss.channel"].browse(res_2["channel_id"])
        visitor_2 = self._get_last_visitor()
        self.assertEqual(channel_2.livechat_visitor_id, visitor_2)
        self.assertEqual(visitor_2, visitor_1)
        channel_2._close_livechat_session()

        # After logout, a new visitor is created and reassigned to the original session
        self.url_open("/web/session/logout")
        self.url_open(self.tracked_page.url)
        visitor_3 = self._get_last_visitor()
        self.assertEqual(channel_1.livechat_visitor_id, visitor_3)
        self.assertNotEqual(visitor_3, visitor_2)
