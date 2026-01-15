# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import HttpCase, tagged, users


@tagged("post_install", "-at_install")
class TestLivechatLead(HttpCase, TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestLivechatLead, cls).setUpClass()
        cls.env["mail.presence"]._update_presence(cls.user_sales_leads)
        cls.livechat_channel = cls.env['im_livechat.channel'].create({
            'name': 'Test Livechat Channel',
            'user_ids': [Command.link(cls.user_sales_leads.id)],
        })
        cls.user_portal = mail_new_test_user(
            cls.env, login='user_portal',
            name='Paulette Portal', email='user_portal@test.example.com',
            company_id=cls.company_main.id,
            notification_type='email',
            groups='base.group_portal',
        )

    @users('user_sales_leads')
    def test_crm_lead_creation_guest(self):
        """ Test customer set on lead: not if public, guest if not public """
        # public: should not be set as customer
        data = self.make_jsonrpc_request("/im_livechat/get_session", {
            'channel_id': self.livechat_channel.id,
            'persisted': True,
        })
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        lead = channel._convert_visitor_to_lead(self.env.user.partner_id, '/lead TestLead command')

        self.assertEqual(lead.origin_channel_id, channel)
        self.assertTrue(any(m.partner_id == self.user_sales_leads.partner_id for m in channel.channel_member_ids))
        self.assertTrue(any(bool(m.guest_id) for m in channel.channel_member_ids))
        self.assertEqual(lead.name, 'TestLead command')
        self.assertEqual(lead.partner_id, self.env['res.partner'])

        # public user: should not be set as customer
        # 'base.public_user' is archived by default
        self.assertFalse(self.env.ref('base.public_user').active)

        data = self.make_jsonrpc_request("/im_livechat/get_session", {
            'channel_id': self.livechat_channel.id,
            'persisted': True,
        })
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        lead = channel._convert_visitor_to_lead(self.env.user.partner_id, '/lead TestLead command')

        self.assertTrue(any(m.partner_id == self.user_sales_leads.partner_id for m in channel.channel_member_ids))
        self.assertTrue(any(bool(m.guest_id) for m in channel.channel_member_ids))

        # public + someone else: no customer (as they were anonymous)
        # sudo: discuss.channel.member - removing non-self member for test setup purposes
        channel.sudo().write({
            'channel_partner_ids': [(4, self.user_sales_manager.partner_id.id)]
        })
        lead = channel._convert_visitor_to_lead(self.env.user.partner_id, '/lead TestLead command')
        self.assertEqual(lead.partner_id, self.env['res.partner'])

    @users('user_sales_leads')
    def test_crm_lead_creation_portal(self):
        # portal: should be set as customer
        self.authenticate("user_portal", "user_portal")
        data = self.make_jsonrpc_request("/im_livechat/get_session", {
            'channel_id': self.livechat_channel.id,
            'persisted': True,
        })
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        lead = channel._convert_visitor_to_lead(self.env.user.partner_id, '/lead TestLead command')

        self.assertEqual(
            channel.channel_partner_ids,
            self.user_sales_leads.partner_id | self.user_portal.partner_id
        )
        self.assertEqual(lead.partner_id, self.user_portal.partner_id)

        # another operator invited: internal user should not be customer if portal is present
        channel.write({
            'channel_partner_ids': [(4, self.user_sales_manager.partner_id.id)]
        })
        lead = channel._convert_visitor_to_lead(self.env.user.partner_id, '/lead TestLead command')

        self.assertEqual(
            channel.channel_partner_ids,
            self.user_sales_leads.partner_id | self.user_portal.partner_id | self.user_sales_manager.partner_id
        )
        self.assertEqual(lead.partner_id, self.user_portal.partner_id)

    def test_create_lead_when_channel_has_deleted_message(self):
        bob_operator = mail_new_test_user(
            self.env, login="bob_user", groups="im_livechat.im_livechat_group_user,sales_team.group_sale_salesman"
        )
        self.authenticate("bob_user", "bob_user")
        self.livechat_channel.user_ids = bob_operator
        self.env["mail.presence"]._update_presence(bob_operator)
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session", {"channel_id": self.livechat_channel.id}
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        message = channel.message_post(
            author_id=bob_operator.partner_id.id,
            body="Hello, how can I help you?",
            message_type="comment",
        )
        channel._message_update_content(message, body="")
        self.env.invalidate_all()
        self.assertFalse(channel.lead_ids)
        channel.with_user(bob_operator).execute_command_lead(body="/lead BobLead")
        self.assertEqual(channel.lead_ids.name, "BobLead")
