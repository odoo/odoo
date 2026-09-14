from odoo import Command
from odoo.tests import tagged, users
from odoo.tools import email_normalize, mute_logger

from odoo.addons.crm.tests.common import INCOMING_EMAIL, TestCrmCommon


@tagged("mail_thread", "mail_gateway")
class NewLeadNotification(TestCrmCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._activate_multi_company()

        cls.test_email = '"Test Email" <test.email@example.com>'
        model_lang = cls.env["res.lang"].sudo().with_context(active_test=False)

        cls.lang_fr = model_lang.search([("code", "=", "fr_FR")])
        if not cls.lang_fr:
            cls.lang_fr = model_lang._create_lang("fr_FR")
        cls.lang_fr.active = False
        cls.lang_en = model_lang.search([("code", "=", "en_US")])
        if not cls.lang_en:
            cls.lang_en = model_lang._create_lang("en_US")
        cls.lang_en.active = True

    @users("user_sales_manager")
    def test_lead_message_get_suggested_recipients(self):
        self.maxDiff = None
        company_partner = self.env["res.partner"].create(
            {
                "name": "test_lead_message_get_suggested_recipients_company_partner",
                "is_company": True,
            }
        )
        partner_no_email = self.env["res.partner"].create(
            {"name": "Test Partner", "email": False}
        )
        leads = self.env["crm.lead"].create(
            [
                {
                    "email_from": '"New Customer" <new.customer.format@test.example.com>',
                    "name": "Test Suggestion (email_from with format)",
                    "partner_name": "Format Name",
                    "user_id": self.user_sales_leads.id,
                },
                {
                    "email_from": "new.customer.multi.1@test.example.com, new.customer.2@test.example.com",
                    "name": "Test Suggestion (email_from multi)",
                    "partner_name": "Multi Name",
                    "user_id": self.user_sales_leads.id,
                },
                {
                    "email_from": "new.customer.with.parent@test.example.com",
                    "name": "Test Suggestion (email_from with matching partner_name)",
                    "partner_name": "test_lead_message_get_suggested_recipients_company_partner",
                    "user_id": self.user_sales_leads.id,
                },
                {
                    "email_from": "new.customer.simple@test.example.com",
                    "name": "Test Suggestion (email_from)",
                    "contact_name": "Std Name",
                    "user_id": self.user_sales_leads.id,
                },
                {
                    "email_from": "test.lang@test.example.com",
                    "lang_id": self.lang_en.id,
                    "name": "Test Suggestion (lang)",
                    "user_id": False,
                },
                {
                    "name": "Test Suggestion (partner_id)",
                    "partner_id": self.contact_1.id,
                    "user_id": self.user_sales_leads.id,
                },
                {
                    "name": "Test Suggestion (partner no email)",
                    "partner_id": partner_no_email.id,
                    "user_id": self.user_sales_leads.id,
                },
                {
                    "name": "Test Suggestion (partner no email with cc email)",
                    "partner_id": partner_no_email.id,
                    "email_cc": "test_cc@odoo.com",
                    "user_id": self.user_sales_leads.id,
                },
            ]
        )
        for lead, expected_suggested in zip(
            leads,
            [
                [
                    {
                        "name": "New Customer",
                        "email": "new.customer.format@test.example.com",
                        "partner_id": False,
                        "create_values": {
                            "is_company": False,
                            "type": "contact",
                            "user_id": self.user_sales_leads.id,
                        },
                    },
                ],
                [
                    {
                        "name": "new.customer.multi.1@test.example.com, new.customer.2@test.example.com",
                        "email": "new.customer.multi.1@test.example.com",
                        "partner_id": False,
                        "create_values": {
                            "is_company": False,
                            "type": "contact",
                            "user_id": self.user_sales_leads.id,
                        },
                    },
                    {
                        "name": "",
                        "email": "new.customer.2@test.example.com",
                        "partner_id": False,
                        "create_values": {},
                    },
                ],
                [
                    {
                        "name": "new.customer.with.parent@test.example.com",
                        "email": "new.customer.with.parent@test.example.com",
                        "partner_id": False,
                        "create_values": {
                            "is_company": False,
                            "parent_id": company_partner.id,
                            "type": "contact",
                            "user_id": self.user_sales_leads.id,
                        },
                    },
                ],
                [
                    {
                        "name": "Std Name",
                        "email": "new.customer.simple@test.example.com",
                        "partner_id": False,
                        "create_values": {
                            "is_company": False,
                            "type": "contact",
                            "user_id": self.user_sales_leads.id,
                        },
                    },
                ],
                [
                    {
                        "name": "test.lang@test.example.com",
                        "email": "test.lang@test.example.com",
                        "partner_id": False,
                        "create_values": {
                            "is_company": False,
                            "lang": "en_US",
                            "type": "contact",
                        },
                    },
                ],
                [
                    {
                        "partner_id": self.contact_1.id,
                        "name": "Philip J Fry",
                        "email": "philip.j.fry@test.example.com",
                        "create_values": {},
                    },
                ],
                [
                    {
                        "partner_id": partner_no_email.id,
                        "name": "Test Partner",
                        "email": False,
                        "create_values": {},
                    },
                ],
                [
                    {
                        "partner_id": partner_no_email.id,
                        "email": False,
                        "name": "Test Partner",
                        "create_values": {},
                    },
                    {
                        "name": "",
                        "email": "test_cc@odoo.com",
                        "partner_id": False,
                        "create_values": {},
                    },
                ],
            ],
        ):
            with self.subTest(lead_name=lead.name, email_from=lead.email_from):
                res = lead._message_get_suggested_recipients(no_create=True)
                self.assertEqual(len(res), len(expected_suggested))
                for received, expected in zip(res, expected_suggested):
                    self.assertDictEqual(received, expected)

    @users("user_sales_manager")
    def test_lead_message_get_suggested_recipients_values_for_create(self):
        lead_details_for_contact = {
            "street": "3rd Floor, Room 3-C",
            "street2": "123 Arlington Avenue",
            "zip": "13202",
            "city": "New York",
            "country_id": self.env.ref("base.us").id,
            "state_id": self.env.ref("base.state_us_39").id,
            "website": "https://www.arlington123.com/3f3c",
            "phone_ids": [
                Command.create({"number": "678-728-0949", "type": "landline"})
            ],
            "function": "Delivery Boy",
            "user_id": self.user_sales_manager.id,
        }

        for partner_name, contact_name, email in [
            (False, "ContactOnly", "test_default_create@example.com"),
            (
                "Delivery Boy company",
                "ContactAndCompany",
                "default_create_with_partner@example.com",
            ),
            (
                "Delivery Boy company",
                "",
                '"Contact Name" <default_create_with_name_in_email@example.com>',
            ),
            (
                "Delivery Boy company",
                "",
                "default_create_with_partner_no_name@example.com",
            ),
            ("", "", "lenny.bar@gmail.com"),
        ]:
            if (
                email
                == '"Contact Name" <default_create_with_name_in_email@example.com>'
            ):
                suggested_email = "default_create_with_name_in_email@example.com"
                suggested_name = "Contact Name"
            else:
                suggested_email = email
                suggested_name = contact_name or email
            with self.subTest(
                partner_name=partner_name, contact_name=contact_name, email=email
            ):
                description = "<p>Top</p>"
                lead1 = self.env["crm.lead"].create(
                    {
                        "name": "TestLead",
                        "contact_name": contact_name,
                        "email_from": email,
                        "lang_id": self.lang_en.id,
                        "description": description,
                        "partner_name": partner_name,
                        **lead_details_for_contact,
                    }
                )
                suggestion = lead1._message_get_suggested_recipients(no_create=True)[0]
                self.assertFalse(suggestion.get("partner_id"))
                self.assertEqual(suggestion["email"], suggested_email)
                self.assertEqual(suggestion["name"], suggested_name)

                create_values = suggestion["create_values"]
                customer_information = lead1._mail_get_customer_information().get(
                    email_normalize(email), {}
                )
                customer_information.pop("name", False)
                self.assertEqual(create_values, customer_information)
                for field, value in lead_details_for_contact.items():
                    if field == "phone_ids":
                        value = [Command.set(lead1.phone_ids.ids)]
                    self.assertEqual(create_values.get(field), value)
                self.assertEqual(create_values["comment"], description)
                self.assertFalse(create_values.get("parent_id"))
                self.assertNotIn("company_name", create_values)
                self.assertEqual(create_values["is_company"], False)

    def test_new_lead_notification(self):
        sales_team_1 = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Test Sales Team",
                "lead_alias_name": "test_sales_team",
            }
        )

        subtype = self.env.ref("crm.mt_salesteam_lead")
        sales_team_1.message_subscribe(
            partner_ids=[self.user_sales_manager.partner_id.id],
            subtype_ids=[subtype.id],
        )

        lead = (
            self.env["crm.lead"]
            .with_context(mail_create_nosubscribe=True)
            .sudo()
            .create(
                {
                    "contact_name": "Somebody",
                    "description": "Some question",
                    "email_from": "somemail@example.com",
                    "name": "Some subject",
                    "partner_name": "Some company",
                    "team_id": sales_team_1.id,
                    "phone_ids": [
                        Command.create({"number": "+0000000000", "type": "landline"})
                    ],
                }
            )
        )
        self.assertIn(self.user_sales_manager.partner_id, lead.message_partner_ids)

        msg = lead.message_ids[0]
        self.assertIn(self.user_sales_manager.partner_id, msg.notified_partner_ids)

        lead_user = lead.with_user(self.user_sales_manager)
        self.assertTrue(lead_user.message_needaction)

    @mute_logger("odoo.addons.mail.models.mixin_mail_thread")
    def test_new_lead_from_email_multicompany(self):
        company0 = self.env.company
        company1 = self.company_2

        self.env.user.write(
            {
                "company_ids": [(4, company0.id, False), (4, company1.id, False)],
            }
        )

        crm_team0 = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "crm team 0",
                "company_id": company0.id,
            }
        )
        crm_team1 = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "crm team 1",
                "company_id": company1.id,
            }
        )

        crm_team0.write(
            {
                "lead_alias_name": "sale_team_0",
                "lead_alias_domain_id": company0.alias_domain_id.id,
            }
        )
        crm_team1.write(
            {
                "lead_alias_name": "sale_team_1",
                "lead_alias_domain_id": company1.alias_domain_id.id,
            }
        )
        mail_alias0 = crm_team0.lead_alias_id.alias_id
        mail_alias1 = crm_team1.lead_alias_id.alias_id

        new_message0 = f"""MIME-Version: 1.0
Date: Thu, 27 Dec 2018 16:27:45 +0100
Message-ID: <blablabla0>
Subject: sale team 0 in company 0
From:  A client <client_a@someprovider.com>
To: {mail_alias0.display_name}
Content-Type: multipart/alternative; boundary="000000000000a47519057e029630"

--000000000000a47519057e029630
Content-Type: text/plain; charset="UTF-8"


--000000000000a47519057e029630
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

<div>A good message</div>

--000000000000a47519057e029630--
"""

        new_message1 = f"""MIME-Version: 1.0
Date: Thu, 27 Dec 2018 16:27:45 +0100
Message-ID: <blablabla1>
Subject: sale team 1 in company 1
From:  B client <client_b@someprovider.com>
To: {mail_alias1.display_name}
Content-Type: multipart/alternative; boundary="000000000000a47519057e029630"

--000000000000a47519057e029630
Content-Type: text/plain; charset="UTF-8"


--000000000000a47519057e029630
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

<div>A good message bis</div>

--000000000000a47519057e029630--
"""
        crm_lead0_id = self.env["mixin.mail.thread"].message_process(
            "crm.lead", new_message0
        )
        crm_lead1_id = self.env["mixin.mail.thread"].message_process(
            "crm.lead", new_message1
        )

        crm_lead0 = self.env["crm.lead"].browse(crm_lead0_id)
        crm_lead1 = self.env["crm.lead"].browse(crm_lead1_id)

        self.assertEqual(crm_lead0.team_id, crm_team0)
        self.assertEqual(crm_lead1.team_id, crm_team1)

        self.assertEqual(crm_lead0.company_id, company0)
        self.assertEqual(crm_lead1.company_id, company1)

    @users("user_sales_manager")
    def test_incoming_email_automatic_lead_assignment(self):
        leader_team_2 = (
            self.env["res.users"].sudo().create({"name": "bob", "login": "bob"})
        )
        team_2 = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "team_2",
                "lead_alias_name": "team.2",
                "user_id": leader_team_2.id,
            }
        )

        for x in range(3):
            self.format_and_process(
                INCOMING_EMAIL,
                f"source.email@customerOfTeam1{x}.be",
                self.sales_team_1.lead_alias_email,
                subject=f"OpportunityTeam1{x}",
                target_model="crm.lead",
            )
            self.format_and_process(
                INCOMING_EMAIL,
                f"source.email@customerOfTeam2{x}.be",
                team_2.lead_alias_email,
                subject=f"OpportunityTeam2{x}",
                target_model="crm.lead",
            )

        team1_leads = self.env["crm.lead"].search(
            [
                ("team_id", "=", self.sales_team_1.id),
                ("email_from", "ilike", "source.email@customerOfTeam"),
            ]
        )
        team2_leads = self.env["crm.lead"].search(
            [
                ("team_id", "=", team_2.id),
                ("email_from", "ilike", "source.email@customerOfTeam"),
            ]
        )
        for lead in team1_leads:
            self.assertTrue("source.email@customerOfTeam1" in lead.email_from)
            self.assertTrue(lead.user_id == self.user_sales_manager)
        for lead in team2_leads:
            self.assertTrue("source.email@customerOfTeam2" in lead.email_from)
            self.assertTrue(lead.user_id == leader_team_2)
