# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestCrmCases


class NewLeadNotification(TestCrmCases):

    def test_new_lead_notification(self):
        """ Test newly create leads like from the website. People and channels
        subscribed to the sales channel shoud be notified. """
        # subscribe a partner and a channel to the sales channel with new lead subtype
        channel_listen = self.env['mail.channel'].create({'name': 'Listener'})
        sales_team_1 = self.env['crm.team'].create({
            'name': 'Test Sales Channel',
            'alias_name': 'test_sales_team',
        })

        subtype = self.env.ref("crm.mt_salesteam_lead")
        sales_team_1.message_subscribe(partner_ids=[self.crm_salesman.partner_id.id], subtype_ids=[subtype.id])
        sales_team_1.message_subscribe(channel_ids=[channel_listen.id], subtype_ids=[subtype.id])

        # Imitate what happens in the controller when somebody creates a new
        # lead from the website form
        lead = self.env["crm.lead"].with_context(mail_create_nosubscribe=True).sudo().create({
            "contact_name": "Somebody",
            "description": "Some question",
            "email_from": "somemail@example.com",
            "name": "Some subject",
            "partner_name": "Some company",
            "team_id": sales_team_1.id,
            "phone": "+0000000000"
        })
        # partner and channel should be auto subscribed
        self.assertIn(self.crm_salesman.partner_id, lead.message_partner_ids)
        self.assertIn(channel_listen, lead.message_channel_ids)

        msg = lead.message_ids[0]
        self.assertIn(self.crm_salesman.partner_id, msg.needaction_partner_ids)
        self.assertIn(channel_listen, msg.channel_ids)

        # The user should have a new unread message
        lead_user = lead.sudo(self.crm_salesman)
        self.assertTrue(lead_user.message_needaction)
