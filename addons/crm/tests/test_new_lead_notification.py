# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestCrm


class NewLeadNotification(TestCrm):

    def test_new_lead_notification(self):
        """ Test newly create leads like from the website. People and channels
        subscribed to the sales channel shoud be notified. """
        # subscribe a partner and a channel to the sales channel with new lead subtype
        subtype = self.env.ref("crm.mt_salesteam_lead")
        self.sales_team_1.message_subscribe(partner_ids=[self.user_salesman_all.partner_id.id], subtype_ids=[subtype.id])
        self.sales_team_1.message_subscribe(channel_ids=[self.channel_listen.id], subtype_ids=[subtype.id])

        # Imitate what happens in the controller when somebody creates a new
        # lead from the website form
        lead = self.env["crm.lead"].with_context(mail_create_nosubscribe=True).sudo().create({
            "contact_name": "Somebody",
            "description": "Some question",
            "email_from": "somemail@example.com",
            "name": "Some subject",
            "partner_name": "Some company",
            "team_id": self.sales_team_1.id,
            "phone": "+0000000000"
        })
        # partner and channel should be auto subscribed
        self.assertIn(self.user_salesman_all.partner_id, lead.message_partner_ids)
        self.assertIn(self.channel_listen, lead.message_channel_ids)

        msg = lead.message_ids[0]
        self.assertIn(self.user_salesman_all.partner_id, msg.needaction_partner_ids)
        self.assertIn(self.channel_listen, msg.channel_ids)

        # The user should have a new unread message
        lead_user = lead.sudo(self.user_salesman_all)
        self.assertTrue(lead_user.message_needaction)
