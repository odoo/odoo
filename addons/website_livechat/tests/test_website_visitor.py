import logging

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website.tests.test_website_visitor import WebsiteVisitorTestsCommon

_logger = logging.getLogger(__name__)


@tagged("-at_install", "post_install")
class TestVisitorUpsertLivechat(TransactionCase):
    def test_new_visitor_links_existing_guest_chat(self):
        guest = self.env["mail.guest"].create({"name": "Visitor guest"})
        channel = self.env["discuss.channel"].create(
            {
                "name": "Existing guest chat",
                "channel_type": "livechat",
                "livechat_operator_id": self.env.user.partner_id.id,
                "channel_member_ids": [Command.create({"guest_id": guest.id})],
            }
        )
        visitor_model = self.env["website.visitor"].with_context(guest=guest)
        website = self.env.ref("website.default_website")
        with MockRequest(visitor_model.env, website=website, country_code="BE"):
            visitor_id, created = visitor_model._upsert_visitor("d" * 32)
        _logger.debug(
            "Guest chat link: visitor=%s created=%s channel_visitor=%s",
            visitor_id,
            created,
            channel.livechat_visitor_id.id,
        )
        self.assertTrue(created)
        self.assertEqual(channel.livechat_visitor_id.id, visitor_id)
        self.assertEqual(channel.country_id.code, "BE")


@tagged("website_visitor")
class WebsiteVisitorTestsLivechat(WebsiteVisitorTestsCommon):
    def test_link_to_visitor_livechat(self):
        [main_visitor, linked_visitor] = self.env["website.visitor"].create(
            [self._prepare_main_visitor_data(), self._prepare_linked_visitor_data()]
        )
        all_discuss_channels = (main_visitor + linked_visitor).discuss_channel_ids
        linked_visitor._merge_visitor(main_visitor)

        self.assertVisitorDeactivated(linked_visitor, main_visitor)

        self.assertEqual(len(main_visitor.discuss_channel_ids), 2)
        self.assertEqual(main_visitor.discuss_channel_ids, all_discuss_channels)

    def _prepare_main_visitor_data(self):
        values = super()._prepare_main_visitor_data()
        test_partner = self.env["res.partner"].create({"name": "John Doe"})
        values.update(
            {
                "partner_id": test_partner.id,
                "discuss_channel_ids": [
                    Command.create(
                        {
                            "name": "Conversation 1",
                            "livechat_end_dt": fields.Datetime.now(),
                        }
                    ),
                ],
            }
        )
        return values

    def _prepare_linked_visitor_data(self):
        values = super()._prepare_linked_visitor_data()
        values.update(
            {
                "discuss_channel_ids": [
                    Command.create(
                        {
                            "name": "Conversation 2",
                            "livechat_end_dt": fields.Datetime.now(),
                        }
                    ),
                ],
            }
        )
        return values

    def test_visitor_page_statistics_access(self):
        operator = new_test_user(
            self.env, "operator", groups="im_livechat.im_livechat_group_user"
        )
        visitor = self._get_last_visitor()
        visitor.with_user(operator).page_count
        with self.assertRaises(AccessError):
            visitor.with_user(operator).page_ids

    def test_visitor_id_continuity_across_sessions(self):
        self.set_registry_readonly_mode(False)

        operator = self.user_admin
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Awesome Channel",
                "user_ids": [Command.set([operator.id])],
            }
        )
        self.env["mail.presence"]._update_presence(operator)

        self.url_open(self.tracked_page.url)
        res_1 = self.call_jsonrpc(
            "/im_livechat/get_session",
            {
                "channel_id": livechat_channel.id,
            },
        )
        channel_1 = self.env["discuss.channel"].browse(res_1["channel_id"])
        visitor_1 = self._get_last_visitor()
        self.assertEqual(channel_1.livechat_visitor_id, visitor_1)
        channel_1._close_livechat_session()

        self._authenticate_via_web(self.user_portal.login, "portal")
        res_2 = self.call_jsonrpc(
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

        self.url_open("/web/session/logout")
        self.url_open(self.tracked_page.url)
        visitor_3 = self._get_last_visitor()
        self.assertEqual(channel_1.livechat_visitor_id, visitor_3)
        self.assertNotEqual(visitor_3, visitor_2)
