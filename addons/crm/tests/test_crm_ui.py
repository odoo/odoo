from odoo import Command
from odoo.tests import Form, HttpCase, TransactionCase
from odoo.tests.common import tagged

from odoo.addons.crm.tests.common import TestCrmCommon


@tagged("post_install", "-at_install")
class TestUi(HttpCase, TestCrmCommon):
    def test_01_crm_tour(self):
        self.env["res.partner"].create(
            {
                "name": "Brandon Freeman",
                "email": "brandon.freeman55@example.com",
                "phone_ids": [
                    Command.create({"number": "(355)-687-3262", "type": "landline"})
                ],
                "is_company": True,
            }
        )
        self.start_tour("/odoo", "crm_tour", login="admin")

    def test_02_crm_tour_rainbowman(self):
        self.env["res.users"].create(
            {
                "name": "Temporary CRM User",
                "login": "temp_crm_user",
                "password": "temp_crm_user",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            self.ref("base.group_user"),
                            self.ref("sale.group_sale_salesman"),
                        ],
                    )
                ],
            }
        )
        self.start_tour("/odoo", "crm_rainbowman", login="temp_crm_user")

    def test_03_crm_tour_forecast(self):
        self.start_tour("/odoo", "crm_forecast", login="admin")

    def test_email_and_phone_propagation_edit_save(self):
        self.env["crm.lead"].search([]).unlink()
        user_admin = self.env["res.users"].search([("login", "=", "admin")])

        partner = self.env["res.partner"].create({"name": "Test Partner"})
        lead = self.env["crm.lead"].create(
            {
                "name": "Test Lead Propagation",
                "type": "opportunity",
                "user_id": user_admin.id,
                "partner_id": partner.id,
                "email_from": "test@example.com",
                "phone_ids": [
                    Command.create({"number": "+32 494 44 44 44", "type": "landline"})
                ],
            }
        )
        partner.email = False
        partner.phone_ids = [Command.clear()]

        self.assertFalse(partner.email)
        self.assertFalse(partner.phone_ids)
        self.assertEqual(lead.email_from, "test@example.com")
        self.assertEqual(lead._phone_get_number().number, "+32 494 44 44 44")

        self.assertTrue(lead.partner_email_update)
        self.assertTrue(lead.partner_phone_update)

        self.start_tour(
            "/odoo", "crm_email_and_phone_propagation_edit_save", login="admin"
        )

        self.assertEqual(
            lead.email_from,
            "test@example.com",
            "Should not have changed the lead email",
        )
        self.assertEqual(
            lead._phone_get_number().number,
            "+32 494 44 44 44",
            "Should not have changed the lead phone",
        )
        self.assertEqual(
            partner.email,
            "test@example.com",
            "Should have propagated the lead email on the partner",
        )
        self.assertEqual(
            partner.phone_ids.mapped("number"),
            ["+32 494 44 44 44"],
            "Should have propagated the lead phone on the partner",
        )


class TestCrmKanbanUI(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.child_contact_1, cls.child_contact_2, cls.orphan_contact = cls.env[
            "res.partner"
        ].create(
            [
                {"name": "Child Contact 1"},
                {"name": "Child Contact 2"},
                {"name": "Orphan Contact"},
            ]
        )
        cls.parent_company, cls.childless_company = cls.env["res.partner"].create(
            [
                {"name": "Parent Company", "is_company": True},
                {"name": "Childless Company", "is_company": True},
            ]
        )
        (cls.child_contact_1 + cls.child_contact_2).parent_id = cls.parent_company
        cls.quick_create_form_view = cls.env.ref(
            "crm.quick_create_opportunity_form", raise_if_not_found=False
        )

    def test_kanban_quick_create_form(self):
        lead_form = Form(self.env["crm.lead"], self.quick_create_form_view)
        self.assertFalse(lead_form._get_context("partner_id")["default_parent_id"])

        lead_form.partner_id = self.orphan_contact
        self.assertFalse(lead_form.commercial_partner_id)
        self.assertFalse(lead_form._get_context("partner_id")["default_parent_id"])

        lead_form.partner_id = self.child_contact_1
        self.assertEqual(lead_form.commercial_partner_id, self.parent_company)
        self.assertEqual(
            lead_form._get_context("partner_id")["default_parent_id"],
            self.parent_company.id,
        )
        lead_form.partner_id = self.child_contact_2
        self.assertEqual(lead_form.commercial_partner_id, self.parent_company)
        self.assertEqual(lead_form.partner_id, self.child_contact_2)

        lead_form.commercial_partner_id = self.childless_company
        self.assertEqual(lead_form.commercial_partner_id, self.childless_company)
        self.assertFalse(lead_form.partner_id)
        self.assertEqual(
            lead_form._get_context("partner_id")["default_parent_id"],
            self.childless_company.id,
        )

        lead_form.commercial_partner_id = self.parent_company
        self.assertEqual(lead_form.commercial_partner_id, self.parent_company)
        self.assertFalse(lead_form.partner_id)
        self.assertEqual(
            lead_form._get_context("partner_id")["default_parent_id"],
            self.parent_company.id,
        )

    def test_kanban_quick_create_partner_inherited_details(self):
        no_partner = self.env["res.partner"]
        company = self.childless_company
        company_number, other_number = self.env["phone.number"].create(
            [{"number": "+32 499 00 00 00"}, {"number": "+32 499 00 00 01"}]
        )
        no_number = company_number.browse()
        company.write(
            {
                "email": "childless@test.lan",
                "phone_ids": [Command.set(company_number.ids)],
            }
        )

        test_cases = [
            (
                {"email_from": False, "phone_ids": no_number},
                {
                    "partner_id": company,
                    "email_from": company.email,
                    "phone_ids": company_number,
                },
            ),
            (
                {"email_from": company.email, "phone_ids": no_number},
                {
                    "partner_id": no_partner,
                    "email_from": company.email,
                    "phone_ids": no_number,
                },
            ),
            (
                {"email_from": company.email, "phone_ids": other_number},
                {
                    "partner_id": no_partner,
                    "email_from": company.email,
                    "phone_ids": other_number,
                },
            ),
            (
                {"email_from": company.email, "phone_ids": company_number},
                {
                    "partner_id": company,
                    "email_from": company.email,
                    "phone_ids": company_number,
                },
            ),
            (
                {"email_from": company.email + "n", "phone_ids": company_number},
                {
                    "partner_id": no_partner,
                    "email_from": company.email + "n",
                    "phone_ids": company_number,
                },
            ),
            (
                {
                    "partner_id": self.child_contact_1,
                    "email_from": company.email,
                    "phone_ids": company_number,
                },
                {
                    "partner_name": self.parent_company.name,
                    "partner_id": self.child_contact_1,
                    "email_from": company.email,
                    "phone_ids": company_number,
                },
            ),
        ]
        for form_values, expected_lead_values in test_cases:
            lead_form = Form(self.env["crm.lead"], self.quick_create_form_view)
            lead_form.commercial_partner_id = self.childless_company
            self.assertFalse(lead_form.phone_ids[:])
            self.assertFalse(lead_form.email_from)
            expected_lead_values = {"partner_name": company.name} | expected_lead_values
            with self.subTest(form_values=form_values):
                for field_name, input_value in form_values.items():
                    if field_name == "phone_ids":
                        lead_form.phone_ids.set(input_value)
                    else:
                        lead_form[field_name] = input_value
                lead = lead_form.save()
                for field_name, expected_value in expected_lead_values.items():
                    self.assertEqual(lead[field_name], expected_value)

        self.assertEqual(company.email, "childless@test.lan")
        self.assertEqual(company.phone_ids, company_number)

        lead = self.env["crm.lead"].create(
            {
                "commercial_partner_id": self.childless_company.id,
                "name": "Childless Company's lead",
            }
        )
        self.assertEqual(lead.partner_id, self.childless_company)

        lead = (
            self.env["crm.lead"]
            .with_context(default_partner_id=self.parent_company)
            .create(
                {
                    "commercial_partner_id": self.childless_company.id,
                    "name": "Childless Company's lead",
                }
            )
        )
        self.assertEqual(
            lead.partner_id,
            self.parent_company,
            "Default partner should take precedence over commercial_partner_id",
        )

        orphan = self.orphan_contact
        orphan.write(
            {
                "email": "orphan_individual@example.com",
                "phone_ids": [
                    Command.create({"number": "+32 488 00 00 00", "type": "landline"})
                ],
            }
        )
        child_contact = self.child_contact_1
        child_contact.write(
            {
                "email": "child_contact@example.com",
                "phone_ids": [
                    Command.create({"number": "+32 477 00 00 00", "type": "landline"})
                ],
            }
        )

        test_cases_default = {
            child_contact: {
                "partner_id": child_contact,
                "email_from": child_contact.email,
                "phone_ids": child_contact.phone_ids,
                "partner_name": self.parent_company.name,
                "commercial_partner_id": self.parent_company,
            },
            company: {
                "partner_id": company,
                "email_from": company.email,
                "phone_ids": company.phone_ids,
                "partner_name": company.name,
                "commercial_partner_id": self.env["res.partner"],
            },
            orphan: {
                "partner_id": orphan,
                "email_from": orphan.email,
                "phone_ids": orphan.phone_ids,
                "partner_name": False,
                "commercial_partner_id": self.env["res.partner"],
            },
        }

        for default_partner, expected_lead_values in test_cases_default.items():
            for view in [None, self.quick_create_form_view]:
                with self.subTest(default_partner=default_partner, view=view):
                    lead_form = Form(
                        self.env["crm.lead"].with_context(
                            default_partner_id=default_partner
                        ),
                        view,
                    )
                    for field_name, expected_value in expected_lead_values.items():
                        value = lead_form[field_name]
                        if field_name == "phone_ids":
                            value = value[:]
                        self.assertEqual(value, expected_value)
