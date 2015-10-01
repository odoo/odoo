# -*- coding: utf-8 -*-
import unittest
from openerp.tests.common import TransactionCase

class NewLeadNotificationTest(TransactionCase):
    @unittest.skip("Broken in 9.0. auto_subscribe does not handle channels")
    def test_new_lead_notification(self):
        # Create a new user
        groups = [
            self.env.ref('base.group_user').id,
            self.env.ref('base.group_sale_salesman').id,
        ]
        user = self.env["res.users"].create({
            "name": __file__,
            "login": __file__,
            'groups_id': [(6, 0, groups)],
        })

        chan = self.env['mail.channel'].create({
            'name': 'Follow leads',
            'group_ids': [(6, 0, groups)],
        })

        # Subscribe him to sales department
        team = self.env.ref("sales_team.team_sales_department")
        subtype = self.env.ref("crm.mt_salesteam_lead")
        team.message_subscribe(channel_ids=[chan.id], subtype_ids=[subtype.id])

        # Imitate what happens in the controller when somebody creates a new
        # lead from the website form
        lead = (self.env["crm.lead"]
                .with_context(mail_create_nosubscribe=True)
                .sudo()
                .create({"contact_name": "Somebody",
                         "description": "Some question",
                         "email_from": "somemail@example.com",
                         "name": "Some subject",
                         "partner_name": "Some company",
                         "team_id": team.id,
                         "phone": "+0000000000"}))

        # The user should have a new unread message
        self.assertTrue(lead.sudo(user).message_unread)
