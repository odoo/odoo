# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase


class NewLeadNotificationTest(TransactionCase):
    def test_new_lead_notification(self):
        # Create a new user
        user = self.env["res.users"].create({
            "name": __file__,
            "login": __file__,
        })

        # Subscribe him to website sales
        team = self.env.ref("website.salesteam_website_sales")
        subtype = self.env.ref("crm.mt_salesteam_lead")
        team.sudo(user).message_subscribe_users(subtype_ids=[subtype.id])

        # Imitate what happens in the controller when omebody creates a new
        # lead from the website form
        lead = (self.env["crm.lead"]
                .with_context(mail_create_nosubscribe=True)
                .sudo()
                .create({"contact_name": "Somebody",
                         "description": "Some question",
                         "email_from": "somemail@example.com",
                         "name": "Some subject",
                         "partner_name": "Some company",
                         "section_id": self.env.ref(
                             "website.salesteam_website_sales").id,
                         "phone": "+0000000000"}))

        # The user should have a new unread message
        self.assertTrue(lead.sudo(user).message_unread)
