from datetime import datetime
from unittest.mock import patch

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged, users
from odoo.tools import mute_logger

from odoo.addons.base.tests.test_format_address_mixin import FormatAddressCase
from odoo.addons.crm.models.crm_lead import (
    PARTNER_ADDRESS_FIELDS_TO_SYNC,
    PARTNER_FIELDS_TO_SYNC,
)
from odoo.addons.crm.tests.common import INCOMING_EMAIL, TestCrmCommon
from odoo.addons.mail.tests.common_tracking import MailTrackingDurationMixinCase
from odoo.addons.phone_validation.tools.phone_validation import phone_format


@tagged("lead_internals")
class TestCRMLead(TestCrmCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_ref = cls.env.ref("base.be")
        cls.test_email = '"Test Email" <test.email@example.com>'
        cls.test_phone = "0485112233"

    def assertLeadAddress(self, lead, street, street2, city, lead_zip, state, country):
        self.assertEqual(lead.street, street)
        self.assertEqual(lead.street2, street2)
        self.assertEqual(lead.city, city)
        self.assertEqual(lead.zip, lead_zip)
        self.assertEqual(lead.state_id, state)
        self.assertEqual(lead.country_id, country)

    @users("user_sales_leads")
    def test_crm_lead_contact_fields_mixed(self):
        lead_data = {
            "name": "TestMixed",
            "partner_id": self.contact_1.id,
            "country_id": self.country_ref.id,
            "function": "Parmesan Rappeur",
            "lang_id": self.lang_fr.id,
            "email_from": self.test_email,
            "phone_ids": [
                Command.create({"number": self.test_phone, "type": "landline"})
            ],
        }
        lead = self.env["crm.lead"].create(lead_data)
        self.assertEqual(lead.name, "TestMixed")
        self.assertLeadAddress(
            lead,
            False,
            False,
            False,
            False,
            self.env["res.country.state"],
            self.country_ref,
        )
        for fname in set(PARTNER_FIELDS_TO_SYNC) - set(["function", "lang"]):
            self.assertEqual(
                lead[fname],
                self.contact_1[fname],
                "No user input -> take from contact for field %s" % fname,
            )
        self.assertEqual(
            lead.function,
            "Parmesan Rappeur",
            "User input should take over partner value",
        )
        self.assertEqual(lead.lang_id, self.lang_fr)
        self.assertEqual(lead.partner_name, self.contact_company_1.name)
        self.assertEqual(lead.contact_name, self.contact_1.name)
        self.assertEqual(lead.email_from, self.test_email)
        self.assertEqual(lead._phone_get_number().number, self.test_phone)

        lead.write({"street": "Super Street", "city": "Super City"})
        self.assertLeadAddress(
            lead,
            "Super Street",
            False,
            "Super City",
            False,
            self.env["res.country.state"],
            self.country_ref,
        )

        lead.write({"partner_id": self.contact_company_1.id})
        for fname in PARTNER_ADDRESS_FIELDS_TO_SYNC:
            self.assertEqual(lead[fname], self.contact_company_1[fname])
            self.assertEqual(self.contact_company_1.lang, self.lang_en.code)
            self.assertEqual(lead.lang_id, self.lang_en)

    @users("user_sales_leads")
    def test_crm_lead_compute_commercial_partner(self):
        company_partner, child_partner, orphan_partner = self.env["res.partner"].create(
            [
                {
                    "name": "test_crm_lead_compute_commercial_partner",
                    "is_company": True,
                    "email": "test_crm_lead_compute_commercial_partner@test.lan",
                },
                {"name": "Test Child"},
                {"name": "Test Orphan"},
            ]
        )
        child_partner.parent_id = company_partner
        lead = self.env["crm.lead"].create(
            {
                "name": "Test Lead",
                "partner_name": "test_crm_lead_compute_commercial_partner",
            }
        )
        self.assertEqual(lead.commercial_partner_id, company_partner)
        lead.partner_id = orphan_partner
        self.assertFalse(lead.commercial_partner_id)
        lead.partner_id = child_partner
        self.assertEqual(lead.commercial_partner_id, company_partner)
        lead.write(
            {
                "partner_id": False,
                "partner_name": False,
            }
        )
        self.assertFalse(lead.commercial_partner_id)
        lead.partner_id = company_partner
        self.assertFalse(
            lead.commercial_partner_id,
            "If a partner is its own commercial_partner_id, the lead is considered to have none.",
        )

    @users("user_sales_leads")
    def test_crm_lead_creation_no_partner(self):
        lead_data = {
            "name": "Test",
            "country_id": self.country_ref.id,
            "email_from": self.test_email,
            "phone_ids": [
                Command.create({"number": self.test_phone, "type": "landline"})
            ],
        }
        lead = self.env["crm.lead"].new(lead_data)
        lead.street
        lead = self.env["crm.lead"].create(lead_data)
        self.assertEqual(
            lead.country_id, self.country_ref, "Country should be set on the lead"
        )
        self.assertEqual(lead.email_from, self.test_email)
        self.assertEqual(lead._phone_get_number().number, self.test_phone)
        lead.partner_id = False
        self.assertEqual(
            lead.country_id, self.country_ref, "Country should still be set on the lead"
        )
        self.assertEqual(lead.email_from, self.test_email)
        self.assertEqual(lead._phone_get_number().number, self.test_phone)

    @users("user_sales_manager")
    def test_crm_lead_creation_partner(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "TestLead",
                "contact_name": "Raoulette TestContact",
                "email_from": '"Raoulette TestContact" <raoulette@test.example.com>',
            }
        )
        self.assertEqual(lead.type, "lead")
        self.assertEqual(lead.user_id, self.user_sales_manager)
        self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(lead.stage_id, self.stage_team1_1)
        self.assertEqual(lead.contact_name, "Raoulette TestContact")
        self.assertEqual(
            lead.email_from, '"Raoulette TestContact" <raoulette@test.example.com>'
        )
        self.assertEqual(self.contact_1.lang, self.env.user.lang)

        lead.write({"partner_id": self.contact_1.id})
        self.assertEqual(lead.partner_name, self.contact_company_1.name)
        self.assertEqual(lead.contact_name, self.contact_1.name)
        self.assertEqual(lead.email_from, self.contact_1.email)
        self.assertEqual(lead.street, self.contact_1.street)
        self.assertEqual(lead.city, self.contact_1.city)
        self.assertEqual(lead.zip, self.contact_1.zip)
        self.assertEqual(lead.country_id, self.contact_1.country_id)
        self.assertEqual(lead.lang_id.code, self.contact_1.lang)

    @users("user_sales_manager")
    def test_crm_lead_creation_partner_address(self):
        other_country = self.env.ref("base.fr")
        empty_partner = self.env["res.partner"].create(
            {
                "name": "Empty partner",
                "country_id": other_country.id,
            }
        )
        lead_data = {
            "name": "Test",
            "street": "My street",
            "street2": "My street",
            "city": "My city",
            "zip": "test@odoo.com",
            "state_id": self.env["res.country.state"]
            .create(
                {
                    "name": "My state",
                    "country_id": self.country_ref.id,
                    "code": "MST",
                }
            )
            .id,
            "country_id": self.country_ref.id,
        }
        lead = self.env["crm.lead"].create(lead_data)
        lead.partner_id = empty_partner
        self.assertEqual(
            lead.street, empty_partner.street, "Street should be sync from the Partner"
        )
        self.assertEqual(
            lead.street2,
            empty_partner.street2,
            "Street 2 should be sync from the Partner",
        )
        self.assertEqual(
            lead.city, empty_partner.city, "City should be sync from the Partner"
        )
        self.assertEqual(
            lead.zip, empty_partner.zip, "Zip should be sync from the Partner"
        )
        self.assertEqual(
            lead.state_id,
            empty_partner.state_id,
            "State should be sync from the Partner",
        )
        self.assertEqual(
            lead.country_id,
            empty_partner.country_id,
            "Country should be sync from the Partner",
        )

    @users("user_sales_manager")
    def test_crm_lead_creation_partner_company(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "TestLead",
                "partner_id": self.contact_company.id,
            }
        )
        self.assertEqual(
            lead.contact_name,
            False,
            "Lead contact name should be Falsy when dealing with companies",
        )
        self.assertEqual(
            lead.partner_name,
            self.contact_company.name,
            "Lead company name should be set to partner name if partner is a company",
        )
        self.contact_company.write({"is_company": False})
        lead = self.env["crm.lead"].create(
            {
                "name": "TestLead",
                "partner_id": self.contact_company.id,
            }
        )
        self.assertEqual(
            lead.contact_name,
            self.contact_company.name,
            "Lead contact name should be set to partner name if partner is not a company",
        )
        self.assertFalse(
            lead.partner_name,
            "An individual with no parent lends the lead no company name",
        )

    @users("user_sales_manager")
    def test_crm_lead_creation_partner_no_address(self):
        empty_partner = self.env["res.partner"].create(
            {
                "name": "Empty partner",
                "is_company": True,
                "lang": "en_US",
                "phone_ids": [
                    Command.create({"number": "0485112233", "type": "landline"})
                ],
                "function": "My function",
            }
        )
        lead_data = {
            "name": "Test",
            "contact_name": "Test",
            "street": "My street",
            "country_id": self.country_ref.id,
            "email_from": self.test_email,
            "phone_ids": [
                Command.create({"number": self.test_phone, "type": "landline"})
            ],
            "website": "http://mywebsite.org",
        }
        lead = self.env["crm.lead"].create(lead_data)
        lead.partner_id = empty_partner
        self.assertEqual(
            lead.contact_name, lead_data["contact_name"], "Contact should remain"
        )
        self.assertEqual(
            lead.email_from,
            lead_data["email_from"],
            "Email From should keep its initial value",
        )
        self.assertEqual(
            lead.partner_name,
            empty_partner.name,
            "Partner name should be set as contact is a company",
        )
        self.assertEqual(
            lead.street,
            lead_data["street"],
            "Street should remain since partner has no address field set",
        )
        self.assertEqual(
            lead.street2,
            False,
            "Street2 should remain since partner has no address field set",
        )
        self.assertEqual(
            lead.country_id,
            self.country_ref,
            "Country should remain since partner has no address field set",
        )
        self.assertEqual(
            lead.city,
            False,
            "City should remain since partner has no address field set",
        )
        self.assertEqual(
            lead.zip, False, "Zip should remain since partner has no address field set"
        )
        self.assertEqual(
            lead.state_id,
            self.env["res.country.state"],
            "State should remain since partner has no address field set",
        )
        self.assertEqual(lead.lang_id, self.lang_en)
        self.assertEqual(
            lead._phone_get_number().number,
            self.test_phone,
            "Phone should keep its initial value",
        )
        self.assertEqual(
            lead.function,
            empty_partner.function,
            "Function from partner should be set on the lead",
        )
        self.assertEqual(
            lead.website, lead_data["website"], "Website should keep its initial value"
        )

    @users("user_sales_manager")
    def test_crm_lead_create_pipe_data(self):
        lead = (
            self.env["crm.lead"]
            .with_context(default_user_id=False)
            .create(
                {
                    "name": "Test",
                    "contact_name": "Test Contact",
                    "email_from": self.test_email,
                    "phone_ids": [
                        Command.create({"number": self.test_phone, "type": "landline"})
                    ],
                }
            )
        )
        self.assertEqual(lead.user_id, self.env["res.users"])
        self.assertEqual(lead.team_id, self.env["team.team"])
        self.assertEqual(lead.stage_id, self.stage_gen_1)

        lead = self.env["crm.lead"].create(
            {
                "name": "Test",
                "contact_name": "Test Contact",
                "email_from": self.test_email,
                "phone_ids": [
                    Command.create({"number": self.test_phone, "type": "landline"})
                ],
            }
        )
        self.assertEqual(lead.user_id, self.user_sales_manager)
        self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(lead.stage_id, self.stage_team1_1)

    @users("user_sales_manager")
    def test_crm_lead_currency_sync(self):
        lead_company = (
            self.env["res.company"]
            .sudo()
            .create(
                {
                    "name": "EUR company",
                    "currency_id": self.env.ref("base.EUR").id,
                }
            )
        )
        lead = (
            self.env["crm.lead"]
            .with_company(lead_company)
            .create({"name": "Lead 1", "company_id": lead_company.id})
        )
        self.assertEqual(lead.company_currency, self.env.ref("base.EUR"))

        lead_company.currency_id = self.env.ref("base.CHF")
        lead.update({"company_id": False})
        self.assertEqual(lead.company_currency, self.env.ref("base.CHF"))

    @users("user_sales_manager")
    def test_crm_lead_date_closed(self):
        lead_in_won = self.env["crm.lead"].create(
            {
                "name": "Created in Won",
                "type": "opportunity",
                "stage_id": self.stage_team1_won.id,
                "expected_revenue": 123.45,
            }
        )
        self.assertTrue(
            lead_in_won.date_closed,
            "Lead created in a won stage must have date_closed set",
        )
        self.assertIsInstance(lead_in_won.date_closed, datetime)
        stage_team1_won2 = self.env["crm.stage"].create(
            {
                "name": "Won2",
                "sequence": 75,
                "team_ids": [self.sales_team_1.id],
                "is_won": True,
            }
        )
        old_date_closed = lead_in_won.date_closed
        with freeze_time("2020-02-02 18:00"):
            lead_in_won.stage_id = stage_team1_won2
        self.assertEqual(
            lead_in_won.date_closed,
            old_date_closed,
            "Moving between won stages should not change existing date_closed",
        )
        won_lead = self.lead_team_1_won.with_env(self.env)
        other_lead = self.lead_1.with_env(self.env)
        old_date_closed = won_lead.date_closed
        self.assertTrue(won_lead.date_closed)
        self.assertFalse(other_lead.date_closed)

        leads = won_lead + other_lead
        with freeze_time("2020-02-02 18:00"):
            leads.stage_id = stage_team1_won2
        self.assertEqual(
            won_lead.date_closed, old_date_closed, "Should not change date"
        )
        self.assertEqual(other_lead.date_closed, datetime(2020, 2, 2, 18, 0, 0))

        leads.write({"stage_id": self.stage_team1_2.id})
        self.assertFalse(won_lead.date_closed)
        self.assertFalse(other_lead.date_closed)

        with freeze_time("2020-02-02 18:00"):
            leads.action_set_lost()
        self.assertEqual(won_lead.date_closed, datetime(2020, 2, 2, 18, 0, 0))
        self.assertEqual(other_lead.date_closed, datetime(2020, 2, 2, 18, 0, 0))

    @users("user_sales_leads")
    @freeze_time("2012-01-14")
    def test_crm_lead_lost_date_closed(self):
        lead = self.lead_1.with_env(self.env)
        self.assertFalse(lead.date_closed, "Initially, closed date is not set")
        lead.action_set_lost()
        self.assertEqual(
            lead.date_closed,
            datetime.now(),
            "Closed date is updated after marking lead as lost",
        )

    @users("user_sales_manager")
    def test_crm_lead_meeting_display_fields(self):
        lead = self.env["crm.lead"].create({"name": "Lead With Meetings"})
        meeting_1, meeting_2, meeting_3 = self.env["calendar.event"].create(
            [
                {
                    "name": "Meeting 1 of Lead",
                    "opportunity_id": lead.id,
                    "start": "2022-07-12 08:00:00",
                    "stop": "2022-07-12 10:00:00",
                },
                {
                    "name": "Meeting 2 of Lead",
                    "opportunity_id": lead.id,
                    "start": "2022-07-14 08:00:00",
                    "stop": "2022-07-14 10:00:00",
                },
                {
                    "name": "Meeting 3 of Lead",
                    "opportunity_id": lead.id,
                    "start": "2022-07-15 08:00:00",
                    "stop": "2022-07-15 10:00:00",
                },
            ]
        )

        with freeze_time("2022-07-13 11:00:00"):
            self.assertEqual(
                lead.meeting_display_date, fields.Date.from_string("2022-07-14")
            )
            self.assertEqual(lead.meeting_display_label, "Next Meeting")
            (meeting_2 | meeting_3).unlink()
            self.assertEqual(
                lead.meeting_display_date, fields.Date.from_string("2022-07-12")
            )
            self.assertEqual(lead.meeting_display_label, "Last Meeting")
            meeting_1.unlink()
            self.assertFalse(lead.meeting_display_date)
            self.assertEqual(lead.meeting_display_label, "No Meeting")

    @users("user_sales_manager")
    def test_crm_lead_partner_sync(self):
        lead, partner = self.lead_1.with_user(self.env.user), self.contact_2
        partner_email, partner_phones = self.contact_2.email, self.contact_2.phone_ids
        lead.partner_id = partner

        lead.partner_id = partner
        self.assertEqual(lead.email_from, partner_email)
        self.assertEqual(lead.phone_ids, partner_phones)

        lead.email_from = '"John Zoidberg" <john.zoidberg@test.example.com>'
        lead.phone_ids = [
            Command.clear(),
            Command.create({"number": "+1 202 555 7799", "type": "landline"}),
        ]
        self.assertEqual(
            partner.email, '"John Zoidberg" <john.zoidberg@test.example.com>'
        )
        self.assertEqual(partner.email_normalized, "john.zoidberg@test.example.com")
        self.assertEqual(partner.phone_ids.mapped("number"), ["+1 202 555 7799"])

        partner.email = partner_email
        partner.phone_ids = [
            Command.clear(),
            Command.create({"number": "+1 202 555 6666", "type": "landline"}),
        ]
        self.assertEqual(lead.email_from, partner_email)
        self.assertEqual(lead.phone_ids.mapped("number"), ["+1 202 555 6666"])

        lead.email_from, lead.phone_ids = False, [Command.clear()]
        self.assertFalse(lead.email_from)
        self.assertFalse(lead.phone_ids)
        self.assertEqual(partner.email, partner_email)
        self.assertEqual(partner.phone_ids.mapped("number"), ["+1 202 555 6666"])

    @users("user_sales_manager")
    def test_crm_lead_partner_sync_email_phone(self):
        lead, partner = self.lead_1.with_user(self.env.user), self.contact_2
        with self.debug_mode():
            lead_form = Form(lead)

            partner_phone = self.test_phone_data[2]
            partner_phone_sanitized = phone_format(
                partner_phone, "US", "1", force_format="E164"
            )
            partner_email, partner_email_normalized = (
                self.test_email_data[2],
                self.test_email_data_normalized[2],
            )
            self.assertEqual(partner_phone_sanitized, self.test_phone_data_sanitized[2])
            self.assertEqual(partner.phone_ids.mapped("number"), [partner_phone])
            self.assertEqual(partner.email, partner_email)

            lead_form.partner_id = partner
            self.assertEqual(lead_form.email_from, partner_email)
            self.assertEqual(
                lead_form.phone_ids[:],
                partner.phone_ids,
                "Lead: partner numbers sent to lead",
            )
            self.assertFalse(lead_form.partner_email_update)
            self.assertFalse(lead_form.partner_phone_update)

            lead_form.save()
            self.assertEqual(
                partner.phone_ids.mapped("number"),
                [partner_phone],
                "Lead / Partner: partner values sent to lead",
            )
            self.assertEqual(
                lead.email_from,
                partner_email,
                "Lead / Partner: partner values sent to lead",
            )
            self.assertEqual(
                lead.email_normalized,
                partner_email_normalized,
                "Lead / Partner: equal emails should lead to equal normalized emails",
            )
            self.assertEqual(
                lead.phone_ids,
                partner.phone_ids,
                "Lead / Partner: partner numbers sent to lead",
            )
            self.assertEqual(
                lead.phone_sanitized,
                partner_phone_sanitized,
                "Lead: phone_sanitized computed field on the primary number",
            )

            lead_form.email_from = '"Hermes Conrad" <%s>' % partner_email_normalized
            self.assertFalse(lead_form.partner_email_update)
            lead_form.save()
            self.assertEqual(partner.email, partner_email)

            self.assertEqual(
                self._phone_number(partner_phone_sanitized),
                partner.phone_ids,
                "Formatting-only variant resolves to the same phone.number",
            )
            lead_form.phone_ids.set(self._phone_number(partner_phone_sanitized))
            self.assertFalse(lead_form.partner_phone_update)
            lead_form.save()
            self.assertEqual(partner.phone_ids.mapped("number"), [partner_phone])

            new_email = '"John Zoidberg" <john.zoidberg@test.example.com>'
            new_email_normalized = "john.zoidberg@test.example.com"
            lead_form.email_from = new_email
            self.assertTrue(lead_form.partner_email_update)
            new_phone = "+1 202 555 7799"
            new_phone_sanitized = phone_format(
                new_phone, "US", "1", force_format="E164"
            )
            new_phone_number = self._phone_number(new_phone)
            lead_form.phone_ids.set(new_phone_number)
            self.assertEqual(lead_form.phone_ids[:], new_phone_number)
            self.assertTrue(lead_form.partner_email_update)
            self.assertTrue(lead_form.partner_phone_update)

            lead_form.save()
            self.assertEqual(partner.email, new_email)
            self.assertEqual(partner.email_normalized, new_email_normalized)
            self.assertEqual(partner.phone_ids, new_phone_number)

            lead_form.email_from = False
            lead_form.phone_ids.clear()
            self.assertFalse(lead_form.partner_email_update)
            self.assertFalse(lead_form.partner_phone_update)
            lead_form.save()
            self.assertEqual(partner.email, new_email)
            self.assertEqual(partner.email_normalized, new_email_normalized)
            self.assertEqual(partner.phone_ids, new_phone_number)
            self.assertFalse(lead.phone_ids)
            self.assertFalse(lead.phone_sanitized)
            self.assertEqual(
                partner.phone_sanitized,
                new_phone_sanitized,
                "Partner sanitized should be computed on the primary number",
            )

    @users("user_sales_manager")
    def test_crm_lead_partner_sync_email_phone_corner_cases(self):
        test_email = "amy.wong@test.example.com"
        lead = self.lead_1.with_user(self.env.user)
        lead.write({"phone_ids": [Command.clear()]})
        contact = self.env["res.partner"].create(
            {
                "name": "NoContact Partner",
                "phone_ids": [Command.clear()],
                "email": "",
            }
        )

        with self.debug_mode():
            lead_form = Form(lead)
            self.assertEqual(lead_form.email_from, test_email)
            self.assertFalse(lead_form.partner_email_update)
            self.assertFalse(lead_form.partner_phone_update)

            lead_form.partner_id = contact
            self.assertTrue(lead_form.partner_email_update)
            self.assertFalse(lead_form.partner_phone_update)
            lead_form.email_from = ""
            self.assertFalse(lead_form.partner_email_update)
            lead_form.email_from = False
            self.assertFalse(lead_form.partner_email_update)

            lead_form.phone_ids.set(self._phone_number("+1 202-555-0888"))
            self.assertFalse(lead_form.partner_email_update)
            self.assertTrue(lead_form.partner_phone_update)
            lead_form.phone_ids.clear()
            self.assertFalse(lead_form.partner_phone_update)

            lead.write(
                {
                    "email_from": '"My Name" <%s>' % test_email,
                    "phone_ids": [
                        Command.create(
                            {"number": "+1 202-555-0888", "type": "landline"}
                        )
                    ],
                }
            )
            contact.write(
                {
                    "email": '"My Name" <%s>' % test_email,
                    "phone_ids": [
                        Command.create(
                            {"number": "+1 202-555-0888", "type": "landline"}
                        )
                    ],
                }
            )
            self.assertEqual(lead.phone_ids, contact.phone_ids)

            lead_form = Form(lead)
            self.assertFalse(lead_form.partner_email_update)
            self.assertFalse(lead_form.partner_phone_update)
            lead_form.partner_id = contact
            self.assertFalse(lead_form.partner_email_update)
            self.assertFalse(lead_form.partner_phone_update)
            lead_form.email_from = '"Another Name" <%s>' % test_email
            self.assertFalse(
                lead_form.partner_email_update,
                "Formatting-only change should not trigger write",
            )
            self.assertFalse(
                lead_form.partner_phone_update,
                "Formatting-only change should not trigger write",
            )
            lead_form.phone_ids.set(self._phone_number("2025550888"))
            self.assertFalse(
                lead_form.partner_email_update,
                "Formatting-only change should not trigger write",
            )
            self.assertFalse(
                lead_form.partner_phone_update,
                "Formatting-only change should not trigger write",
            )

            lead_form.phone_ids.set(self._phone_number("666 789456789456789456"))
            self.assertTrue(lead_form.partner_phone_update)

            be_country = self.env.ref("base.be")
            contact.write(
                {
                    "country_id": be_country.id,
                    "phone_ids": [
                        Command.clear(),
                        Command.create({"number": "+32456001122", "type": "landline"}),
                    ],
                }
            )
            lead.write({"country_id": False})
            lead_form = Form(lead)
            lead_form.partner_id = contact
            lead_form.phone_ids.set(
                self._phone_number("0456 00 11 22", country_id=be_country.id)
            )
            self.assertFalse(lead_form.partner_phone_update)
            self.assertEqual(lead_form.country_id, be_country)

    @users("user_sales_manager")
    def test_crm_lead_stages(self):
        first_now = datetime(2023, 11, 6, 8, 0, 0)
        with (
            patch.object(self.env.cr, "now", lambda: first_now),
            freeze_time(first_now),
        ):
            self.lead_1.write({"date_open": first_now})

        lead = self.lead_1.with_user(self.env.user)
        self.assertEqual(lead.date_open, first_now)
        self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(lead.user_id, self.user_sales_leads)

        second_now = datetime(2023, 11, 8, 8, 0, 0)
        with (
            patch.object(self.env.cr, "now", lambda: second_now),
            freeze_time(second_now),
        ):
            lead.convert_opportunity(self.contact_1)
        self.assertEqual(lead.date_open, first_now)
        self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(lead.user_id, self.user_sales_leads)

        lead.action_set_won()
        self.assertEqual(lead.probability, 100.0)
        self.assertEqual(lead.stage_id, self.stage_gen_won)

    def test_crm_lead_stages_with_multiple_possible_teams(self):
        self.sales_team_2 = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Test Sales Team 2",
                "company_id": False,
                "user_id": self.user_sales_manager.id,
            }
        )
        self.sales_team_2_m1 = self.env["team.member"].create(
            {
                "user_id": self.user_sales_leads.id,
                "team_id": self.sales_team_2.id,
            }
        )

        user_teams = self.env["team.team"].search(
            [
                ("team_member_all_ids.user_id", "=", self.user_sales_leads.id),
            ]
        )
        self.assertIn(self.sales_team_1, user_teams)
        self.assertIn(self.sales_team_2, user_teams)

        self.stage_team2_1 = self.env["crm.stage"].create(
            {
                "name": "New (T2)",
                "team_ids": [self.sales_team_2.id],
            }
        )

        lead = (
            self.env["crm.lead"]
            .with_user(self.user_sales_leads)
            .create(
                {
                    "name": "Test",
                    "contact_name": "Test Contact",
                    "team_id": self.sales_team_1.id,
                }
            )
        )
        self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(lead.stage_id, self.stage_team1_1)

        lead.team_id = self.sales_team_2
        self.assertEqual(lead.team_id, self.sales_team_2)
        self.assertEqual(lead.stage_id, self.stage_team2_1)

    @users("user_sales_manager")
    def test_crm_lead_unlink_calendar_event(self):
        lead = self.env["crm.lead"].create({"name": "Lead With Meetings"})
        meetings = self.env["calendar.event"].create(
            [
                {
                    "name": "Meeting 1 of Lead",
                    "res_id": lead.id,
                    "res_model_id": self.env["ir.model"]._get_id(lead._name),
                    "start": "2022-07-12 08:00:00",
                    "stop": "2022-07-12 10:00:00",
                },
                {
                    "name": "Meeting 2 of Lead",
                    "opportunity_id": lead.id,
                    "res_id": lead.id,
                    "res_model_id": self.env["ir.model"]._get_id(lead._name),
                    "start": "2022-07-13 08:00:00",
                    "stop": "2022-07-13 10:00:00",
                },
            ]
        )
        self.assertEqual(len(lead.calendar_event_ids), 1)
        self.assertEqual(meetings.opportunity_id, lead)
        self.assertEqual(meetings.mapped("res_id"), [lead.id, lead.id])
        self.assertEqual(meetings.mapped("res_model"), ["crm.lead", "crm.lead"])
        lead.unlink()
        self.assertEqual(meetings.exists(), meetings)
        self.assertFalse(meetings.opportunity_id)
        self.assertEqual(set(meetings.mapped("res_id")), set([0]))
        self.assertEqual(set(meetings.mapped("res_model")), set([False]))

    @users("user_sales_leads")
    def test_crm_lead_update_contact(self):
        self.assertFalse(self.contact_company_1.phone_ids)
        self.assertEqual(self.contact_company_1.country_id.code, "US")
        lead = self.env["crm.lead"].create(
            {
                "name": "Test",
                "country_id": self.country_ref.id,
                "email_from": self.test_email,
                "phone_ids": [
                    Command.create({"number": self.test_phone, "type": "landline"})
                ],
            }
        )
        self.assertEqual(
            lead.country_id, self.country_ref, "Country should be set on the lead"
        )
        lead.partner_id = False
        self.assertEqual(
            lead.country_id, self.country_ref, "Country should still be set on the lead"
        )
        self.assertEqual(lead.email_from, self.test_email)
        self.assertEqual(lead._phone_get_number().number, self.test_phone)
        self.assertEqual(lead.email_state, "correct")
        self.assertEqual(lead.phone_state, "correct")

        lead.partner_id = self.contact_company_1
        self.assertEqual(
            lead.country_id,
            self.contact_company_1.country_id,
            "Country should still be the one set on partner",
        )
        self.assertEqual(lead.email_from, self.contact_company_1.email)
        self.assertEqual(lead._phone_get_number().number, self.test_phone)
        self.assertEqual(lead.email_state, "correct")
        self.assertEqual(
            lead.phone_state,
            "incorrect",
            "Belgian phone with US country -> considered as incorrect",
        )

        lead.email_from = "broken"
        lead.phone_ids = [
            Command.clear(),
            Command.create({"number": "alsobroken", "type": "landline"}),
        ]
        self.assertEqual(lead.email_state, "incorrect")
        self.assertEqual(lead.phone_state, "incorrect")
        self.assertEqual(self.contact_company_1.email, "broken")
        self.assertEqual(
            self.contact_company_1.phone_ids.mapped("number"), ["alsobroken"]
        )

    @users("user_sales_manager")
    def test_crm_lead_update_dates_are_per_record(self):
        first_now = datetime(2024, 3, 1, 8, 0, 0)
        with (
            patch.object(self.env.cr, "now", lambda: first_now),
            freeze_time(first_now),
        ):
            settled = self.env["crm.lead"].create(
                [
                    {
                        "name": f"Settled_{index}",
                        "stage_id": self.stage_team1_1.id,
                        "team_id": self.sales_team_1.id,
                        "type": "opportunity",
                        "user_id": self.user_sales_salesman.id,
                    }
                    for index in range(3)
                ]
            )
            mover = self.env["crm.lead"].create(
                {
                    "name": "Mover",
                    "stage_id": self.stage_team1_2.id,
                    "team_id": self.sales_team_1.id,
                    "type": "opportunity",
                    "user_id": self.user_sales_leads.id,
                }
            )
            (settled + mover).flush_recordset()
        for lead in settled + mover:
            self.assertEqual(lead.date_open, first_now)
            self.assertEqual(lead.date_last_stage_update, first_now)

        later = datetime(2024, 3, 20, 8, 0, 0)
        with patch.object(self.env.cr, "now", lambda: later), freeze_time(later):
            (settled + mover).write(
                {
                    "stage_id": self.stage_team1_1.id,
                    "user_id": self.user_sales_salesman.id,
                }
            )
            (settled + mover).flush_recordset()

        self.assertEqual(mover.date_open, later, "Its salesperson changed")
        self.assertEqual(mover.date_last_stage_update, later, "Its stage changed")
        for lead in settled:
            self.assertEqual(
                lead.date_open,
                first_now,
                "Same salesperson, same stage: untouched, whatever else was in the write",
            )
            self.assertEqual(lead.date_last_stage_update, first_now)

        member = self.env["team.member"].search(
            [
                ("team_id", "=", self.sales_team_1.id),
                ("user_id", "=", self.user_sales_salesman.id),
            ],
            limit=1,
        )
        if member:
            member.invalidate_recordset(["lead_day_count"])
            self.assertEqual(
                member.lead_day_count,
                1,
                "Only the lead that really changed hands counts against the daily quota",
            )

    @users("user_sales_manager")
    def test_crm_lead_won_stage_is_the_teams_own(self):
        team_other = self.env["team.team"].create(
            {"use_sale": True, "name": "Other Team"}
        )
        stage_other, stage_other_won = self.env["crm.stage"].create(
            [
                {"name": "Other New", "sequence": 1, "team_ids": [team_other.id]},
                {
                    "name": "Other Won",
                    "sequence": 10,
                    "team_ids": [team_other.id],
                    "is_won": True,
                },
            ]
        )
        lead_team_1 = self.env["crm.lead"].create(
            {
                "name": "Team 1 opportunity",
                "stage_id": self.stage_team1_1.id,
                "team_id": self.sales_team_1.id,
                "type": "opportunity",
            }
        )
        lead_other = self.env["crm.lead"].create(
            {
                "name": "Other team opportunity",
                "stage_id": stage_other.id,
                "team_id": team_other.id,
                "type": "opportunity",
            }
        )

        (lead_team_1 + lead_other).action_set_won()

        self.assertEqual(lead_other.stage_id, stage_other_won)
        for lead in lead_team_1 + lead_other:
            self.assertTrue(lead.stage_id.is_won)
            if lead.stage_id.team_ids:
                self.assertIn(
                    lead.team_id,
                    lead.stage_id.team_ids,
                    f"{lead.name} was moved into a stage reserved for another team",
                )

    @users("user_sales_manager")
    def test_crm_lead_update_dates(self):
        first_now = datetime(2023, 11, 6, 8, 0, 0)
        with (
            patch.object(self.env.cr, "now", lambda: first_now),
            freeze_time(first_now),
        ):
            leads = self.env["crm.lead"].create(
                [
                    {
                        "email_from": "testlead@customer.company.com",
                        "name": "Lead_1",
                        "team_id": self.sales_team_1.id,
                        "type": "lead",
                        "user_id": False,
                    },
                    {
                        "email_from": "testopp@customer.company.com",
                        "name": "Opp_1",
                        "type": "opportunity",
                        "user_id": self.user_sales_salesman.id,
                    },
                ]
            )
            leads.flush_recordset()
        for lead in leads:
            self.assertEqual(
                lead.date_last_stage_update,
                first_now,
                "Stage updated at create time with default value",
            )
            self.assertEqual(lead.stage_id, self.stage_team1_1)
            self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertFalse(leads[0].date_open, "No user -> no assign date")
        self.assertFalse(leads[0].user_id)
        self.assertEqual(leads[1].date_open, first_now, "Default user assigned")
        self.assertEqual(
            leads[1].user_id, self.user_sales_salesman, "Default user assigned"
        )

        updated_time = datetime(2023, 11, 23, 8, 0, 0)
        with (
            patch.object(self.env.cr, "now", lambda: updated_time),
            freeze_time(updated_time),
        ):
            leads.write({"user_id": self.user_sales_salesman.id})
            leads.flush_recordset()
        for lead in leads:
            self.assertEqual(lead.stage_id, self.stage_team1_1)
            self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(
            leads[0].date_last_stage_update,
            first_now,
            "Setting same stage when changing user_id, should not update",
        )
        self.assertEqual(
            leads[0].date_open, updated_time, "User assigned -> assign date updated"
        )
        self.assertEqual(
            leads[1].date_last_stage_update,
            first_now,
            "Setting same stage when changing user_id, should not update",
        )
        self.assertEqual(
            leads[1].date_open,
            first_now,
            "Same user_id: date_open is untouched, even though the other lead in "
            "the same write did change hands",
        )

        newer_time = datetime(2023, 11, 26, 8, 0, 0)
        with (
            patch.object(self.env.cr, "now", lambda: newer_time),
            freeze_time(newer_time),
        ):
            leads[1].action_set_won()
            leads[1].flush_recordset()
        self.assertEqual(
            leads[1].date_last_stage_update,
            newer_time,
            "Mark as won updates stage hence stage update date",
        )
        self.assertEqual(leads[1].stage_id, self.stage_gen_won)

        last_time = datetime(2023, 11, 29, 8, 0, 0)
        with (
            patch.object(self.env.cr, "now", lambda: last_time),
            freeze_time(last_time),
        ):
            leads.merge_opportunity(
                user_id=self.user_sales_salesman.id,
                auto_unlink=False,
            )
            leads.flush_recordset()
        self.assertEqual(leads[0].date_last_stage_update, first_now)
        self.assertEqual(leads[0].date_open, updated_time)
        self.assertEqual(leads[0].stage_id, self.stage_team1_1)
        self.assertEqual(leads[0].team_id, self.sales_team_1)
        self.assertEqual(
            leads[1].date_last_stage_update,
            newer_time,
            "Should not rewrite when setting same stage",
        )
        self.assertEqual(
            leads[1].date_open,
            first_now,
            "Should not rewrite when setting same user_id: this lead has had the "
            "same salesperson since it was created",
        )
        self.assertEqual(leads[1].stage_id, self.stage_gen_won)
        self.assertEqual(leads[1].team_id, self.sales_team_1)
        self.assertEqual(leads[1].user_id, self.user_sales_salesman)

    @users("user_sales_manager")
    def test_crm_team_alias(self):
        new_team = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "TestAlias",
                "use_leads": True,
                "use_opportunities": True,
                "lead_alias_name": "test.alias",
            }
        )
        self.assertEqual(new_team.lead_alias_id.alias_name, "test.alias")
        self.assertEqual(new_team.lead_alias_name, "test.alias")

        new_team.write(
            {
                "use_leads": False,
                "use_opportunities": False,
            }
        )

    @users("user_sales_manager")
    def test_crm_team_alias_helper(self):
        self.env["team.team"].search([]).active = False
        self.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )

        self._activate_multi_company()
        team_other_comp = self.team_company2

        user_team_leads, team_leads, user_team_opport, team_opport = self.env[
            "team.team"
        ].create(
            [
                {
                    "use_sale": True,
                    "name": "UserTeamLeads",
                    "company_id": self.env.company.id,
                    "use_leads": True,
                    "member_ids": [(6, 0, [self.env.user.id])],
                },
                {
                    "use_sale": True,
                    "name": "TeamLeads",
                    "company_id": self.env.company.id,
                    "use_leads": True,
                    "member_ids": [],
                },
                {
                    "use_sale": True,
                    "name": "UserTeamOpportunities",
                    "company_id": self.env.company.id,
                    "use_leads": False,
                    "member_ids": [(6, 0, [self.env.user.id])],
                },
                {
                    "use_sale": True,
                    "name": "TeamOpportunities",
                    "company_id": self.env.company.id,
                    "use_leads": False,
                    "member_ids": [],
                },
            ]
        )

        user_team_leads.invalidate_recordset(fnames=["member_ids"])
        self.assertEqual(user_team_leads.member_ids.ids, [self.env.user.id])

        self.env["crm.lead"].create(
            [
                {
                    "name": "LeadOurTeam",
                    "team_id": user_team_leads.id,
                    "type": "lead",
                },
                {
                    "name": "LeadTeam",
                    "team_id": team_leads.id,
                    "type": "lead",
                },
                {
                    "name": "OpportunityOurTeam",
                    "team_id": user_team_opport.id,
                    "type": "opportunity",
                },
                {
                    "name": "OpportunityTeam",
                    "team_id": team_opport.id,
                    "type": "opportunity",
                },
            ]
        )
        self.env["crm.lead"].with_user(self.user_sales_manager_mc).create(
            {
                "name": "LeadOtherComp",
                "team_id": team_other_comp.id,
                "type": "lead",
                "company_id": self.company_2.id,
            }
        )

        teams = [
            user_team_leads,
            team_leads,
            user_team_opport,
            team_opport,
            team_other_comp,
        ]
        for team in teams:
            team.lead_alias_id.sudo().write({"alias_name": team.name})

        for team in teams:
            with self.subTest(team=team):
                if team != team_other_comp:
                    self.assertIn(
                        f"<a href='mailto:{team.lead_alias_email}'>{team.lead_alias_email}</a>",
                        self.env["crm.lead"].sudo().get_empty_list_help(""),
                    )
                else:
                    self.assertNotIn(
                        f"<a href='mailto:{team.lead_alias_email}'>{team.lead_alias_email}</a>",
                        self.env["crm.lead"].sudo().get_empty_list_help(""),
                    )
                team.active = False

    @mute_logger("odoo.addons.mail.models.mixin_mail_thread")
    def test_mailgateway(self):
        new_lead = self.format_and_process(
            INCOMING_EMAIL,
            "unknown.sender@test.example.com",
            self.sales_team_1.lead_alias_email,
            subject="Delivery cost inquiry",
            target_model="crm.lead",
        )
        self.assertEqual(new_lead.email_from, "unknown.sender@test.example.com")
        self.assertFalse(new_lead.partner_id)
        self.assertEqual(new_lead.name, "Delivery cost inquiry")

        message = new_lead.with_user(self.user_sales_manager).message_post(
            body="Here is my offer!", subtype_xmlid="mail.mt_comment"
        )
        self.assertEqual(message.author_id, self.user_sales_manager.partner_id)

        new_lead._handle_partner_assignment(create_missing=True)
        self.assertEqual(new_lead.partner_id.email, "unknown.sender@test.example.com")

    @users("user_sales_manager")
    def test_phone_mobile_search(self):
        lead_1 = self.env["crm.lead"].create(
            {
                "name": "Lead 1",
                "country_id": self.env.ref("base.be").id,
                "phone_ids": [
                    Command.create({"number": "+32485001122", "type": "landline"})
                ],
            }
        )
        lead_2 = self.env["crm.lead"].create(
            {
                "name": "Lead 2",
                "country_id": self.env.ref("base.be").id,
                "phone_ids": [
                    Command.create({"number": "0032485001122", "type": "landline"})
                ],
            }
        )
        lead_3 = self.env["crm.lead"].create(
            {
                "name": "Lead 3",
                "country_id": self.env.ref("base.be").id,
                "phone_ids": [Command.create({"number": "hello", "type": "landline"})],
            }
        )
        lead_4 = self.env["crm.lead"].create(
            {
                "name": "Lead 3",
                "country_id": self.env.ref("base.be").id,
                "phone_ids": [
                    Command.create({"number": "+32485112233", "type": "landline"})
                ],
            }
        )

        self.env["crm.lead"].search([("phone_mobile_search", "like", "")])
        with self.assertRaises(UserError):
            self.env["crm.lead"].search([("phone_mobile_search", "like", "7   ")])
        with self.assertRaises(UserError):
            self.env["crm.lead"].search([("phone_mobile_search", "like", "c")])
        with self.assertRaises(UserError):
            self.env["crm.lead"].search([("phone_mobile_search", "like", "+")])
        with self.assertRaises(UserError):
            self.env["crm.lead"].search([("phone_mobile_search", "like", "5")])
        with self.assertRaises(UserError):
            self.env["crm.lead"].search([("phone_mobile_search", "like", "42")])

        self.assertEqual(
            lead_1 + lead_2,
            self.env["crm.lead"].search(
                [("phone_mobile_search", "like", "+32485001122")]
            ),
        )
        self.assertEqual(
            lead_1 + lead_2,
            self.env["crm.lead"].search(
                [("phone_mobile_search", "like", "0032485001122")]
            ),
        )
        self.assertEqual(
            lead_1 + lead_2,
            self.env["crm.lead"].search([("phone_mobile_search", "like", "485001122")]),
        )
        self.assertEqual(
            lead_1 + lead_2 + lead_4,
            self.env["crm.lead"].search([("phone_mobile_search", "like", "1122")]),
        )

        self.assertEqual(
            self.env["crm.lead"].search([("phone_mobile_search", "like", "hello")]),
            lead_3,
            "Should behave like a text field",
        )
        self.assertFalse(
            self.env["crm.lead"].search([("phone_mobile_search", "like", "Hello")]),
            "Should behave like a text field (case sensitive)",
        )
        self.assertEqual(
            self.env["crm.lead"].search([("phone_mobile_search", "ilike", "Hello")]),
            lead_3,
            "Should behave like a text field (case insensitive)",
        )
        self.assertEqual(
            self.env["crm.lead"].search([("phone_mobile_search", "like", "hello123")]),
            self.env["crm.lead"],
            "Should behave like a text field",
        )

    @users("user_sales_manager")
    def test_phone_mobile_search_format(self):
        numbers = [
            "0499223311",
            "0499/223311",
            "0499/22.33.11",
            "0499/22 33 11",
            "0499/223 311",
        ]
        leads = self.env["crm.lead"].create(
            [
                {
                    "name": "Lead %s" % index,
                    "country_id": self.env.ref("base.be").id,
                    "phone_ids": [
                        Command.create({"number": number, "type": "landline"})
                    ],
                }
                for index, number in enumerate(numbers)
            ]
        )

        self.assertEqual(
            leads,
            self.env["crm.lead"].search(
                [("phone_mobile_search", "like", "0499223311")]
            ),
        )
        self.assertEqual(
            leads,
            self.env["crm.lead"].search(
                [("phone_mobile_search", "like", "0499/223311")]
            ),
        )
        self.assertEqual(
            leads,
            self.env["crm.lead"].search(
                [("phone_mobile_search", "like", "0499/22.33.11")]
            ),
        )
        self.assertEqual(
            leads,
            self.env["crm.lead"].search(
                [("phone_mobile_search", "like", "0499/22 33 11")]
            ),
        )
        self.assertEqual(
            leads,
            self.env["crm.lead"].search(
                [("phone_mobile_search", "like", "0499/223 311")]
            ),
        )

    @users("user_sales_manager")
    def test_phone_mobile_update(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Lead 1",
                "country_id": self.env.ref("base.us").id,
                "phone_ids": [
                    Command.create(
                        {"number": self.test_phone_data[0], "type": "landline"}
                    )
                ],
            }
        )
        self.assertEqual(lead._phone_get_number().number, self.test_phone_data[0])
        self.assertEqual(lead.phone_sanitized, self.test_phone_data_sanitized[0])

        lead.write({"phone_ids": [Command.clear()]})
        self.assertFalse(lead.phone_ids)
        self.assertEqual(lead.phone_sanitized, False)

        lead.write(
            {
                "phone_ids": [
                    Command.create(
                        {"number": self.test_phone_data[1], "type": "landline"}
                    )
                ]
            }
        )
        self.assertEqual(lead._phone_get_number().number, self.test_phone_data[1])
        self.assertEqual(lead.phone_sanitized, self.test_phone_data_sanitized[1])

        lead.write({"country_id": self.env.ref("base.be").id})
        self.assertEqual(lead._phone_get_number().number, self.test_phone_data[1])
        self.assertEqual(
            lead.phone_sanitized,
            self.test_phone_data_sanitized[1],
            "The number keeps its own country, the lead's does not re-sanitize it",
        )


class TestCRMLeadRotting(TestCrmCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stage_team1_1.rotting_threshold_days = 5
        cls.stage_team1_2.rotting_threshold_days = 3

    @users("user_sales_manager")
    def test_leads_rotting(self):
        rotten_leads = self.env["crm.lead"]
        clean_leads = self.env["crm.lead"]

        close_future = datetime(2025, 1, 24, 12, 0, 0)
        now = datetime(2025, 1, 20, 12, 0, 0)
        close_past = datetime(2025, 1, 18, 12, 0, 0)
        past = datetime(2025, 1, 10, 12, 0, 0)
        last_year = datetime(2024, 1, 20, 12, 0, 0)

        with self.mock_datetime_and_now(past):
            rotten_leads += self.env["crm.lead"].create(
                [
                    {
                        "name": "Opportunity",
                        "type": "opportunity",
                        "stage_id": self.stage_team1_1.id,
                    }
                    for x in range(3)
                ]
            )
            rotten_leads.flush_recordset(["date_last_stage_update"])

        with self.mock_datetime_and_now(close_past):
            clean_leads += self.env["crm.lead"].create(
                {
                    "name": "Lead that won't have time to rot",
                    "type": "opportunity",
                    "stage_id": self.stage_team1_1.id,
                }
            )
            clean_leads.flush_recordset(["date_last_stage_update"])
        with self.mock_datetime_and_now(last_year):
            clean_leads += self.env["crm.lead"].create(
                {
                    "name": "Opportuniy in Won Stage",
                    "type": "opportunity",
                    "stage_id": self.stage_gen_won.id,
                }
            )
            clean_leads.flush_recordset(["date_last_stage_update"])

        with self.mock_datetime_and_now(now):
            for lead in rotten_leads:
                self.assertTrue(lead.is_rotting)
                self.assertEqual(lead.rotting_days, 10)
            for lead in clean_leads:
                self.assertFalse(lead.is_rotting)
                self.assertEqual(lead.rotting_days, 0)

            rotten_leads_iterator = iter(rotten_leads)

            lead_edited = next(rotten_leads_iterator)
            lead_edited.name = "Edited Opportunity"
            self.assertTrue(
                lead_edited.is_rotting,
                "Editing the lead has no effect on rotting status",
            )

            lead_changed_stage = next(rotten_leads_iterator)
            lead_changed_stage.stage_id = self.stage_team1_2.id
            self.assertFalse(
                lead_changed_stage.is_rotting,
                "Changing the stage disables rotting status",
            )

            lead_changed_rotting_threshold = next(rotten_leads_iterator)
            old_rotting_threshold = self.stage_team1_1.rotting_threshold_days
            self.stage_team1_1.rotting_threshold_days = 50
            self.assertFalse(
                lead_changed_rotting_threshold.is_rotting,
                "Changing the rotting threshold to a higher value does affect rotten leads' status",
            )
            self.stage_team1_1.rotting_threshold_days = old_rotting_threshold
            self.assertTrue(
                lead_changed_rotting_threshold.is_rotting,
                "Changing the threshold back should affect the status again",
            )

            self.stage_team1_1.rotting_threshold_days = 0
            self.assertFalse(
                lead_changed_rotting_threshold.is_rotting,
                "A 0-day rotting threshold disables rotting",
            )
            self.stage_team1_1.rotting_threshold_days = old_rotting_threshold

            jan20_lead = self.env["crm.lead"].create(
                {
                    "name": "Fresh Opportuniy",
                    "type": "opportunity",
                    "stage_id": self.stage_team1_1.id,
                }
            )

        with self.mock_datetime_and_now(close_future):
            rotten_leads.invalidate_recordset(["is_rotting", "rotting_days"])
            self.assertEqual(
                lead_changed_rotting_threshold.rotting_days,
                14,
                "Since this lead has not seen a stage change, it has been rotting for 14 days total",
            )
            self.assertFalse(
                jan20_lead.is_rotting,
                "Since this lead remained in a stage with a higher threshold, it's not rotting yet",
            )
            self.assertTrue(
                lead_changed_stage.is_rotting,
                "As its new stage has a lower rotting threshold, this lead should be rotting 3 days after its last stage change",
            )
            self.assertEqual(lead_changed_stage.rotting_days, 4)

    def test_search_leads_rotting(self):
        past = datetime(2025, 1, 1)
        now = datetime(2025, 1, 10)
        with self.mock_datetime_and_now(past):
            all_leads = self.env["crm.lead"].create(
                [
                    {
                        "name": "TestLead Rotting opportunity",
                        "type": "opportunity",
                        "stage_id": self.stage_team1_1.id,
                    }
                ]
                * 5
                + [
                    {
                        "name": "TestLead Lead",
                        "type": "lead",
                        "stage_id": self.stage_team1_1.id,
                    }
                ]
                * 3
                + [
                    {
                        "name": "TestLead Won Opportunity",
                        "type": "opportunity",
                        "stage_id": self.stage_gen_won.id,
                    }
                ]
                * 4
            )

            all_leads.flush_recordset(["date_last_stage_update"])
            rotten_leads = all_leads.filtered(lambda lead: "Rotting" in lead.name)
            clean_leads = all_leads - rotten_leads

        with self.mock_datetime_and_now(now):
            rot = self.env["crm.lead"].search(
                [
                    ("name", "ilike", "TestLead"),
                    ("is_rotting", "=", True),
                ],
                order="id ASC",
            )
            norot = self.env["crm.lead"].search(
                [
                    ("name", "ilike", "TestLead"),
                    ("is_rotting", "=", False),
                ],
                order="id ASC",
            )

            self.assertEqual(rot, rotten_leads)
            self.assertEqual(norot, clean_leads)


@tagged("lead_internals")
class TestLeadFormTools(FormatAddressCase):
    def test_address_view(self):
        self.env.company.country_id = self.env.ref("base.us")
        self.assertAddressView("crm.lead")


@tagged("lead_internals", "is_query_count")
class TestCrmLeadMailTrackingDuration(MailTrackingDurationMixinCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass("crm.lead")

    def test_crm_lead_mail_tracking_duration(self):
        self._test_record_duration_tracking()

    def test_crm_lead_mail_tracking_duration_batch(self):
        self._test_record_duration_tracking_batch()

    def test_crm_lead_queries_batch_mail_tracking_duration(self):
        self._test_queries_batch_duration_tracking()


@tagged("lead_internals")
class TestLeadTeamIsAlive(TestCrmCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["team.team"].search([]).action_archive()
        cls.dead_team = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Archived Team",
                "company_id": False,
                "user_id": cls.user_sales_manager.id,
                "use_leads": True,
            }
        )
        cls.dead_team.action_archive()

    def test_no_archived_team_whatever_the_active_test(self):
        for active_test in (True, False):
            with self.subTest(active_test=active_test):
                lead = (
                    self.env["crm.lead"]
                    .with_context(
                        active_test=active_test,
                    )
                    .create({"name": "Alive?", "type": "lead"})
                )
                lead.user_id = self.user_sales_manager.id
                lead.flush_recordset()
                self.assertFalse(
                    lead.team_id,
                    "the only team is archived, so the lead gets none",
                )


@tagged("post_install", "-at_install")
class TestLeadEmptyListHelp(TestCrmCommon):
    """The pipeline's empty-list help is built for whoever opened the view, and
    it looks the team alias up by the model that alias creates. Reaching that
    model through `alias_model_id.model` makes the ORM resolve the condition
    with an access-checked search on `ir.model`, which no salesman may read.
    """

    @users("user_sales_salesman")
    def test_empty_list_help_names_the_team_alias(self):
        help_html = self.env["crm.lead"].get_empty_list_help("")
        self.assertIn(
            self.sales_team_1.lead_alias_email,
            help_html,
            "the help offers the lead-creating team's alias, so the lookup ran",
        )

    @users("user_sales_salesman")
    def test_empty_list_help_keeps_given_help(self):
        self.assertEqual(
            self.env["crm.lead"].get_empty_list_help("<p>Given</p>"),
            "<p>Given</p>",
        )
