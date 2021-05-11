# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import users


class TestLivechatLead(TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestLivechatLead, cls).setUpClass()

        cls.user_anonymous = mail_new_test_user(
            cls.env, login='user_anonymous',
            name='Anonymous Website', email=False,
            company_id=cls.company_main.id,
            notification_type='inbox',
            groups='base.group_public',
        )
        cls.user_portal = mail_new_test_user(
            cls.env, login='user_portal',
            name='Paulette Portal', email='user_portal@test.example.com',
            company_id=cls.company_main.id,
            notification_type='inbox',
            groups='base.group_portal',
        )

    @users('user_sales_leads')
    def test_crm_lead_creation_guest(self):
        """ Test customer set on lead: not if public, guest if not public """
        # public: should not be set as customer
        channel = self.env['mail.channel'].create({
            'name': 'Chat with Visitor',
            'channel_partner_ids': [(4, self.user_anonymous.partner_id.id)]
        })
        lead = channel._convert_visitor_to_lead(self.env.user.partner_id, '/lead TestLead command')

        self.assertEqual(
            channel.channel_partner_ids,
            self.user_sales_leads.partner_id | self.user_anonymous.partner_id
        )
        self.assertEqual(lead.name, 'TestLead command')
        self.assertEqual(lead.partner_id, self.env['res.partner'])

        # public user: should not be set as customer
        # 'base.public_user' is archived by default
        self.assertFalse(self.env.ref('base.public_user').active)

        channel = self.env['mail.channel'].create({
            'name': 'Chat with Visitor',
            'channel_partner_ids': [(4, self.env.ref('base.public_partner').id)]
        })
        lead = channel._convert_visitor_to_lead(self.env.user.partner_id, '/lead TestLead command')

        self.assertEqual(
            channel.channel_last_seen_partner_ids.partner_id,
            self.user_sales_leads.partner_id | self.env.ref('base.public_partner')
        )
        self.assertEqual(lead.name, 'TestLead command')
        self.assertEqual(lead.partner_id, self.env['res.partner'])

        # public + someone else: no customer (as he was anonymous)
        channel.write({
            'channel_partner_ids': [(4, self.user_sales_manager.partner_id.id)]
        })
        lead = channel._convert_visitor_to_lead(self.env.user.partner_id, '/lead TestLead command')
        self.assertEqual(lead.partner_id, self.env['res.partner'])

        # portal: should be set as customer
        channel = self.env['mail.channel'].create({
            'name': 'Chat with Visitor',
            'channel_partner_ids': [(4, self.user_portal.partner_id.id)]
        })
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
