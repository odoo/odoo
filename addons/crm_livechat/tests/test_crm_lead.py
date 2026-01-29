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

        cls.env['bus.presence'].create({'user_id': cls.user_sales_leads.id, 'status': 'online'})
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
        channel_info = self.make_jsonrpc_request("/im_livechat/get_session", {
            'anonymous_name': 'Visitor',
            'channel_id': self.livechat_channel.id,
            'persisted': True,
        })
        channel = self.env['discuss.channel'].browse(channel_info['id'])
        lead = channel._convert_visitor_to_lead(self.env.user.partner_id, '/lead TestLead command')

        self.assertTrue(any(m.partner_id == self.user_sales_leads.partner_id for m in channel.channel_member_ids))
        self.assertTrue(any(bool(m.guest_id) for m in channel.channel_member_ids))
        self.assertEqual(lead.name, 'TestLead command')
        self.assertEqual(lead.partner_id, self.env['res.partner'])

        # public user: should not be set as customer
        # 'base.public_user' is archived by default
        self.assertFalse(self.env.ref('base.public_user').active)

        channel_info = self.make_jsonrpc_request("/im_livechat/get_session", {
            'anonymous_name': 'Visitor',
            'channel_id': self.livechat_channel.id,
            'persisted': True,
        })
        channel = self.env['discuss.channel'].browse(channel_info['id'])
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
        channel_info = self.make_jsonrpc_request("/im_livechat/get_session", {
            'anonymous_name': 'Visitor',
            'channel_id': self.livechat_channel.id,
            'persisted': True,
        })
        channel = self.env['discuss.channel'].browse(channel_info['id'])
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
