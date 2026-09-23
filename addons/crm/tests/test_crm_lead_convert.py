from itertools import product

from odoo import SUPERUSER_ID, Command
from odoo.fields import Datetime
from odoo.tests import Form, tagged, users

from odoo.addons.crm.tests import common as crm_common


@tagged("lead_manage")
class TestLeadConvertForm(crm_common.TestLeadConvertCommon):
    @users("user_sales_manager")
    def test_form_action_default(self):
        lead = self.env["crm.lead"].browse(self.lead_1.ids)
        customer = self.env["res.partner"].create(
            {
                "name": "Amy Wong",
                "email": '"Amy, PhD Student, Wong" Tiny <AMY.WONG@test.example.com>',
            }
        )

        wizard = Form(
            self.env["crm.lead2opportunity.partner"].with_context(
                {
                    "active_model": "crm.lead",
                    "active_id": lead.id,
                    "active_ids": lead.ids,
                }
            )
        )

        self.assertEqual(wizard.name, "convert")
        self.assertEqual(wizard.action, "exist")
        self.assertEqual(wizard.partner_id, customer)

    @users("user_sales_manager")
    def test_form_name_onchange(self):
        lead = self.env["crm.lead"].browse(self.lead_1.ids)
        lead_dup = lead.copy({"name": "Duplicate"})
        customer = self.env["res.partner"].create(
            {
                "name": "Amy Wong",
                "email": '"Amy, PhD Student, Wong" Tiny <AMY.WONG@test.example.com>',
            }
        )

        wizard = Form(
            self.env["crm.lead2opportunity.partner"].with_context(
                {
                    "active_model": "crm.lead",
                    "active_id": lead.id,
                    "active_ids": lead.ids,
                }
            )
        )

        self.assertEqual(wizard.name, "merge")
        self.assertEqual(wizard.action, "exist")
        self.assertEqual(wizard.partner_id, customer)
        self.assertEqual(wizard.duplicated_lead_ids[:], lead + lead_dup)

        wizard.name = "convert"
        wizard.action = "create"
        self.assertEqual(wizard.action, "create", "Should keep user input")
        self.assertEqual(wizard.name, "convert", "Should keep user input")


@tagged("lead_manage")
class TestLeadConvert(crm_common.TestLeadConvertCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        date = Datetime.from_string("2020-01-20 16:00:00")
        cls.crm_lead_dt_mock.now.return_value = date

    @users("user_sales_manager")
    def test_duplicates_computation(self):
        test_lead = self.env["crm.lead"].browse(self.lead_1.ids)
        customer, dup_leads = self._create_duplicates(test_lead)
        dup_leads += self.env["crm.lead"].create(
            [
                {
                    "name": "Duplicate lead: same email_from, lost",
                    "type": "lead",
                    "email_from": test_lead.email_from,
                    "probability": 0,
                    "active": False,
                },
                {
                    "name": "Duplicate lead: same email_from, archived (not lost)",
                    "type": "lead",
                    "email_from": test_lead.email_from,
                    "probability": 50,
                    "active": False,
                },
                {
                    "name": "Duplicate lead: same email_from, proba 0 but not lost",
                    "type": "lead",
                    "email_from": test_lead.email_from,
                    "probability": 0,
                    "active": True,
                },
                {
                    "name": "Duplicate opp: same email_from, won",
                    "type": "opportunity",
                    "email_from": test_lead.email_from,
                    "probability": 100,
                    "stage_id": self.stage_team1_won.id,
                },
                {
                    "name": "Duplicate opp: same email_from, proba 100 but not won",
                    "type": "opportunity",
                    "email_from": test_lead.email_from,
                    "probability": 100,
                    "stage_id": self.stage_team1_2.id,
                },
                {
                    "name": "Duplicate opp: same email_from, archived (not lost)",
                    "type": "opportunity",
                    "email_from": test_lead.email_from,
                    "probability": 50,
                    "stage_id": self.stage_team1_2.id,
                    "active": False,
                },
            ]
        )
        self.assertEqual(len(dup_leads), 10, "Be sure below quick access are relevant")
        opp_lost = dup_leads[3]
        lead_lost = dup_leads[4]
        lead_archived = dup_leads[5]
        opp_won = dup_leads[7]
        _opp_proba100 = dup_leads[8]
        opp_archived = dup_leads[9]

        test_lead.write({"partner_id": customer.id})

        result = test_lead._get_lead_duplicates(
            partner=test_lead.partner_id, email=test_lead.email_from, include_lost=False
        )
        self.assertEqual(
            result,
            test_lead
            + dup_leads
            - (lead_lost + lead_archived + opp_won + opp_archived + opp_lost),
            "Should not include: lost lead or opp, archived lead / opp (aka: only active lead/opp not won nor lost)",
        )

        result = test_lead._get_lead_duplicates(
            partner=test_lead.partner_id,
            email=test_lead.email_from,
            include_lost=True,
        )
        self.assertEqual(
            result, test_lead + dup_leads - (lead_lost + lead_archived + opp_won)
        )

    def test_initial_data(self):
        self.assertFalse(self.lead_1.date_conversion)
        self.assertEqual(
            self.lead_1.date_open, Datetime.from_string("2020-01-15 11:30:00")
        )
        self.assertEqual(self.lead_1.lang_id, self.lang_fr)
        self.assertEqual(self.lead_1._phone_get_number().number, "+1 202 555 9999")
        self.assertEqual(self.lead_1.user_id, self.user_sales_leads)
        self.assertEqual(self.lead_1.team_id, self.sales_team_1)
        self.assertEqual(self.lead_1.stage_id, self.stage_team1_1)

    @users("user_sales_manager")
    def test_lead_convert_base(self):
        self.contact_2.phone_ids = [Command.clear()]
        self.assertFalse(self.contact_2.phone_ids)
        lead = self.lead_1.with_user(self.env.user)
        lead.write(
            {
                "phone_ids": [
                    Command.clear(),
                    Command.create({"number": "123456789", "type": "landline"}),
                ],
            }
        )
        self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(lead.stage_id, self.stage_team1_1)
        self.assertEqual(lead.email_from, "amy.wong@test.example.com")
        self.assertEqual(lead.lang_id, self.lang_fr)
        lead.convert_opportunity(self.contact_2)

        self.assertEqual(lead.type, "opportunity")
        self.assertEqual(lead.partner_id, self.contact_2)
        self.assertEqual(lead.email_from, self.contact_2.email)
        self.assertEqual(lead.lang_id, self.lang_en)
        self.assertEqual(lead._phone_get_number().number, "123456789")
        self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(lead.stage_id, self.stage_team1_1)

    @users("user_sales_manager")
    def test_lead_convert_base_corner_cases(self):
        lead = self.lead_1.with_user(self.env.user)
        lead.action_archive()
        self.assertFalse(lead.active)
        lead.convert_opportunity(self.contact_2)

        self.assertEqual(lead.type, "lead")
        self.assertEqual(lead.partner_id, self.env["res.partner"])

        lead.action_unarchive()
        self.assertTrue(lead.active)

        lead.action_set_won()
        self.assertEqual(lead.stage_id, self.stage_gen_won)
        self.assertEqual(lead.probability, 100)

        lead.convert_opportunity(self.contact_2)
        self.assertEqual(lead.type, "lead")
        self.assertEqual(lead.partner_id, self.env["res.partner"])

    @users("user_sales_manager")
    def test_lead_convert_base_w_salesmen(self):
        lead = self.lead_1.with_user(self.env.user)
        self.assertEqual(lead.team_id, self.sales_team_1)
        lead.convert_opportunity(False, user_ids=self.user_sales_salesman.ids)
        self.assertEqual(lead.user_id, self.user_sales_salesman)
        self.assertEqual(lead.team_id, self.sales_team_convert)

    @users("user_sales_manager")
    def test_lead_convert_base_w_team(self):
        lead = self.lead_1.with_user(self.env.user)
        lead.convert_opportunity(False, team_id=self.sales_team_convert.id)
        self.assertEqual(lead.team_id, self.sales_team_convert)
        self.assertEqual(lead.user_id, self.user_sales_leads)

    @users("user_sales_manager")
    def test_lead_convert_corner_cases_crud(self):
        other_lead = self.lead_1.copy()
        other_lead.write({"partner_id": self.contact_1.id})

        convert = (
            self.env["crm.lead2opportunity.partner"]
            .with_context(
                {
                    "default_lead_id": other_lead.id,
                }
            )
            .create({})
        )
        self.assertEqual(convert.lead_id, other_lead)
        self.assertEqual(convert.partner_id, self.contact_1)
        self.assertEqual(convert.action, "exist")

        convert = (
            self.env["crm.lead2opportunity.partner"]
            .with_context(
                {
                    "default_lead_id": other_lead.id,
                    "active_model": "crm.lead",
                    "active_id": self.lead_1.id,
                }
            )
            .create({})
        )
        self.assertEqual(convert.lead_id, other_lead)
        self.assertEqual(convert.partner_id, self.contact_1)
        self.assertEqual(convert.action, "exist")

    @users("user_sales_manager")
    def test_lead_convert_corner_cases_matching(self):
        self.lead_1.write({"email_from": "Amy Wong <amy.wong@test.example.com>"})
        self.env["res.partner"].create(
            {"name": "Different Name", "email": "Wong AMY <AMY.WONG@test.example.com>"}
        )

        self.env["crm.lead2opportunity.partner"].with_context(
            {
                "active_model": "crm.lead",
                "active_id": self.lead_1.id,
                "active_ids": self.lead_1.ids,
            }
        ).create({})

    @users("user_sales_manager")
    def test_lead_convert_no_lang(self):
        inactive_lang = (
            self.env["res.lang"]
            .sudo()
            .create(
                {
                    "code": "en_ZZ",
                    "name": "Inactive Lang",
                    "active": False,
                }
            )
        )

        lead = self.lead_1.with_user(self.env.user)
        lead.lang_id = inactive_lang

        convert = (
            self.env["crm.lead2opportunity.partner"]
            .with_context(
                {
                    "active_model": "crm.lead",
                    "active_id": self.lead_1.id,
                    "active_ids": self.lead_1.ids,
                }
            )
            .create({"action": "create"})
        )
        convert.action_apply()
        self.assertTrue(lead.partner_id)
        self.assertEqual(lead.partner_id.lang, "en_US")

    @users("user_sales_manager")
    def test_lead_convert_internals(self):
        convert = (
            self.env["crm.lead2opportunity.partner"]
            .with_context(
                {
                    "active_model": "crm.lead",
                    "active_id": self.lead_1.id,
                    "active_ids": self.lead_1.ids,
                }
            )
            .create({})
        )

        self.assertEqual(convert.lead_id, self.lead_1)
        self.assertEqual(convert.user_id, self.lead_1.user_id)
        self.assertEqual(convert.team_id, self.lead_1.team_id)
        self.assertFalse(convert.partner_id)
        self.assertEqual(convert.name, "convert")
        self.assertEqual(convert.action, "create")

        convert.write({"user_id": self.user_sales_salesman.id})
        self.assertEqual(convert.user_id, self.user_sales_salesman)
        self.assertEqual(convert.team_id, self.sales_team_convert)

        convert.action_apply()
        self.assertEqual(self.lead_1.type, "opportunity")
        self.assertEqual(self.lead_1.user_id, self.user_sales_salesman)
        self.assertEqual(self.lead_1.team_id, self.sales_team_convert)
        new_partner = self.lead_1.partner_id
        self.assertEqual(new_partner.email, "amy.wong@test.example.com")
        self.assertEqual(new_partner.lang, self.lang_fr.code)
        self.assertEqual(new_partner._phone_get_number().number, "+1 202 555 9999")
        self.assertEqual(new_partner.name, "Amy Wong")

    @users("user_sales_manager")
    def test_lead_convert_action_exist(self):
        self.lead_1.write({"partner_id": self.contact_1.id})

        convert = (
            self.env["crm.lead2opportunity.partner"]
            .with_context(
                {
                    "active_model": "crm.lead",
                    "active_id": self.lead_1.id,
                    "active_ids": self.lead_1.ids,
                }
            )
            .create({})
        )
        self.assertEqual(convert.action, "exist")
        convert.action_apply()
        self.assertEqual(self.lead_1.type, "opportunity")
        self.assertEqual(self.lead_1.partner_id, self.contact_1)

    @users("user_sales_manager")
    def test_lead_convert_contact_mutlicompany(self):
        company_2 = (
            self.env["res.company"]
            .with_user(SUPERUSER_ID)
            .create({"name": "Company 2"})
        )
        partner_company_2 = (
            self.env["res.partner"]
            .with_user(SUPERUSER_ID)
            .create(
                {
                    "name": "Contact in other company",
                    "email": "test@company2.com",
                    "company_id": company_2.id,
                }
            )
        )
        lead = self.env["crm.lead"].create(
            {
                "name": "LEAD",
                "type": "lead",
                "email_from": "test@company2.com",
            }
        )
        convert = (
            self.env["crm.lead2opportunity.partner"]
            .with_context(
                {
                    "active_model": "crm.lead",
                    "active_id": lead.id,
                    "active_ids": lead.ids,
                }
            )
            .create({"name": "convert", "action": "exist"})
        )
        self.assertNotEqual(
            convert.partner_id,
            partner_company_2,
            "Conversion wizard should not be able to find the partner from another company",
        )

    @users("user_sales_manager")
    def test_lead_convert_same_partner(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Empty partner",
            }
        )
        lead = self.env["crm.lead"].create(
            {
                "name": "LEAD",
                "partner_id": partner.id,
                "type": "lead",
                "email_from": "demo@test.com",
                "lang_id": self.lang_fr.id,
                "street": "my street",
                "city": "my city",
            }
        )
        lead.convert_opportunity(partner)
        self.assertEqual(
            lead.email_from,
            "demo@test.com",
            "Email From should be preserved during conversion",
        )
        self.assertEqual(
            lead.lang_id, self.lang_fr, "Lang should be preserved during conversion"
        )
        self.assertEqual(
            lead.street, "my street", "Street should be preserved during conversion"
        )
        self.assertEqual(
            lead.city, "my city", "City should be preserved during conversion"
        )
        self.assertEqual(partner.lang, "en_US")

    @users("user_sales_manager")
    def test_lead_convert_properties_preserve(self):
        initial_team = self.lead_1.with_env(self.env).team_id
        self.lead_1.lead_properties = [
            {
                "name": "test",
                "type": "char",
                "value": "test value",
                "definition_changed": True,
            }
        ]
        self.lead_1.convert_opportunity(False)
        self.assertEqual(self.lead_1.team_id, initial_team)
        self.assertEqual(self.lead_1.lead_properties, {"test": "test value"})

        self.lead_1.write({"team_id": self.lead_1.team_id.id})
        self.assertEqual(self.lead_1.lead_properties, {"test": "test value"})

    @users("user_sales_manager")
    def test_lead_convert_properties_reset(self):
        initial_team = self.lead_1.with_env(self.env).team_id
        self.lead_1.lead_properties = [
            {
                "name": "test",
                "type": "char",
                "value": "test value",
                "definition_changed": True,
            }
        ]
        self.lead_1.convert_opportunity(False, user_ids=self.user_sales_salesman.ids)
        self.assertNotEqual(self.lead_1.team_id, initial_team)
        self.assertFalse(self.lead_1.lead_properties)

    @users("user_sales_manager")
    def test_lead_convert_wizard_new_partner(self):
        no_partner = self.env["res.partner"]
        test_partner_lead, test_partner_wizard, commercial_partner = self.env[
            "res.partner"
        ].create(
            [
                {"name": "Lead Test Partner"},
                {"name": "Wizard Test Partner"},
                {"name": "Company Partner", "is_company": True},
            ]
        )
        case_values = product(
            [no_partner, test_partner_lead],
            [False, "New Company"],
            [no_partner, commercial_partner],
            [no_partner, test_partner_wizard],
            ["create", "exist"],
        )
        for (
            lead_partner,
            lead_company_name,
            wizard_company,
            wizard_contact,
            wizard_action,
        ) in case_values:
            (test_partner_lead + test_partner_wizard).parent_id = False
            commercial_partner.invalidate_recordset()
            lead_contact_name = lead_partner.name or "Test Contact Name"
            lead = self.env["crm.lead"].create(
                {
                    "name": "Test Lead",
                    "contact_name": lead_contact_name,
                    "partner_id": lead_partner.id,
                    "partner_name": lead_company_name,
                }
            )
            wizard = (
                self.env["crm.lead2opportunity.partner"]
                .with_context(
                    {
                        "active_model": "crm.lead",
                        "active_id": lead.id,
                        "active_ids": lead.ids,
                    }
                )
                .create({})
            )
            wizard.write({"action": wizard_action, "name": "convert"})
            if wizard_contact:
                wizard.partner_id = wizard_contact
            if wizard_company:
                wizard.commercial_partner_id = wizard_company
            with self.subTest(
                lead_company_name=lead_company_name,
                lead_partner=lead_partner.name,
                wizard_company=wizard_company.name,
                wizard_contact=wizard_contact.name,
                wizard_action=wizard_action,
            ):
                wizard.action_apply()
                self.assertEqual(lead.type, "opportunity")
                self.assertEqual(
                    bool(lead.partner_id),
                    bool(wizard_action == "create" or lead_partner or wizard_contact),
                )
                if wizard_action == "exist" and (lead_partner or wizard_contact):
                    self.assertEqual(lead.partner_id, wizard_contact or lead_partner)
                if (
                    wizard_action == "create"
                    and not lead_partner
                    and not wizard_contact
                    and wizard_company
                ):
                    self.assertTrue(lead.partner_id)
                    self.assertEqual(lead.partner_id.name, lead_contact_name)
                    self.assertEqual(lead.partner_id.parent_id, wizard_company)
                if wizard_action == "create" and (wizard_contact or lead_partner):
                    self.assertEqual(lead.partner_id, wizard_contact or lead_partner)
                    self.assertFalse(lead.partner_id.parent_id)

    @users("user_sales_manager")
    def test_lead_merge(self):
        date = Datetime.from_string("2020-01-20 16:00:00")
        self.crm_lead_dt_mock.now.return_value = date

        leads = self.env["crm.lead"]
        for x in range(2):
            leads |= self.env["crm.lead"].create(
                {
                    "name": "Dup-%02d-%s" % (x + 1, self.lead_1.name),
                    "type": "lead",
                    "user_id": False,
                    "team_id": self.lead_1.team_id.id,
                    "contact_name": "Duplicate %02d of %s"
                    % (x + 1, self.lead_1.contact_name),
                    "email_from": self.lead_1.email_from,
                    "probability": 10,
                }
            )

        convert = (
            self.env["crm.lead2opportunity.partner"]
            .with_context(
                {
                    "active_model": "crm.lead",
                    "active_id": self.lead_1.id,
                    "active_ids": self.lead_1.ids,
                }
            )
            .create({})
        )

        self.assertEqual(convert.duplicated_lead_ids, self.lead_1 | leads)
        self.assertEqual(convert.user_id, self.lead_1.user_id)
        self.assertEqual(convert.team_id, self.lead_1.team_id)
        self.assertFalse(convert.partner_id)
        self.assertEqual(convert.name, "merge")
        self.assertEqual(convert.action, "create")

        convert.write({"user_id": self.user_sales_salesman.id})
        self.assertEqual(convert.user_id, self.user_sales_salesman)
        self.assertEqual(convert.team_id, self.sales_team_convert)

        convert.action_apply()
        self.assertEqual(self.lead_1.type, "opportunity")

    @users("user_sales_manager")
    def test_lead_merge_last_created(self):
        date = Datetime.from_string("2020-01-20 16:00:00")
        self.crm_lead_dt_mock.now.return_value = date

        last_lead = self.env["crm.lead"].create(
            {
                "name": f"Duplicate of {self.lead_1.contact_name}",
                "type": "lead",
                "user_id": False,
                "team_id": self.lead_1.team_id.id,
                "contact_name": f"Duplicate of {self.lead_1.contact_name}",
                "email_from": self.lead_1.email_from,
                "probability": 10,
            }
        )

        convert = (
            self.env["crm.lead2opportunity.partner"]
            .with_context(
                {
                    "active_model": "crm.lead",
                    "active_id": last_lead.id,
                    "active_ids": last_lead.ids,
                }
            )
            .create({})
        )

        self.assertEqual(convert.lead_id, last_lead)
        convert.action_apply()
        self.assertTrue(convert.exists(), "Wizard cannot be deleted via cascade!")
        self.assertEqual(
            convert.lead_id, self.lead_1, "Lead must be the result opportunity!"
        )
        self.assertEqual(self.lead_1.type, "opportunity")
        self.assertFalse(
            last_lead.exists(), "The last lead must be merged with the first one!"
        )

    @users("user_sales_salesman")
    def test_lead_merge_user(self):
        date = Datetime.from_string("2020-01-20 16:00:00")
        self.crm_lead_dt_mock.now.return_value = date

        leads = self.env["crm.lead"]
        for x in range(2):
            leads |= self.env["crm.lead"].create(
                {
                    "name": "Dup-%02d-%s" % (x + 1, self.lead_1.name),
                    "type": "lead",
                    "user_id": False,
                    "team_id": self.lead_1.team_id.id,
                    "contact_name": "Duplicate %02d of %s"
                    % (x + 1, self.lead_1.contact_name),
                    "email_from": self.lead_1.email_from,
                    "probability": 10,
                }
            )

        convert = (
            self.env["crm.lead2opportunity.partner"]
            .with_context(
                {
                    "active_model": "crm.lead",
                    "active_id": leads[0].id,
                    "active_ids": leads[0].ids,
                }
            )
            .create({})
        )

        self.assertEqual(convert.duplicated_lead_ids, leads)
        self.assertEqual(convert.name, "merge")
        self.assertEqual(convert.action, "create")

        convert.write({"user_id": self.user_sales_salesman.id})
        self.assertEqual(convert.user_id, self.user_sales_salesman)
        self.assertEqual(convert.team_id, self.sales_team_convert)

        convert.action_apply()
        self.assertEqual(leads[0].type, "opportunity")

    @users("user_sales_manager")
    def test_lead_merge_duplicates(self):
        customer, dup_leads = self._create_duplicates(self.lead_1)
        lead_partner = dup_leads.filtered(
            lambda lead: lead.name == "Duplicate: customer ID"
        )
        self.assertTrue(bool(lead_partner))

        self.lead_1.write(
            {
                "partner_id": customer.id,
            }
        )
        convert = (
            self.env["crm.lead2opportunity.partner"]
            .with_context(
                {
                    "active_model": "crm.lead",
                    "active_id": self.lead_1.id,
                    "active_ids": self.lead_1.ids,
                }
            )
            .create({})
        )
        self.assertEqual(convert.partner_id, customer)
        self.assertEqual(convert.duplicated_lead_ids, self.lead_1 | dup_leads)

        self.lead_1.write(
            {
                "email_from": False,
                "partner_id": customer.id,
            }
        )
        customer.write({"email": False})
        convert = (
            self.env["crm.lead2opportunity.partner"]
            .with_context(
                {
                    "active_model": "crm.lead",
                    "active_id": self.lead_1.id,
                    "active_ids": self.lead_1.ids,
                }
            )
            .create({})
        )
        self.assertEqual(convert.partner_id, customer)
        self.assertEqual(convert.duplicated_lead_ids, self.lead_1 | lead_partner)

    @users("user_sales_manager")
    def test_lead_merge_duplicates_flow(self):
        self.lead_1.write({"email_from": "Amy Wong <amy.wong@test.example.com>"})
        customer, dup_leads = self._create_duplicates(self.lead_1)
        opp_lost = dup_leads.filtered(
            lambda lead: lead.name == "Duplicate: lost opportunity"
        )
        self.assertTrue(bool(opp_lost))

        convert = (
            self.env["crm.lead2opportunity.partner"]
            .with_context(
                {
                    "active_model": "crm.lead",
                    "active_id": self.lead_1.id,
                    "active_ids": self.lead_1.ids,
                }
            )
            .create({})
        )
        self.assertEqual(convert.partner_id, customer)
        self.assertEqual(convert.duplicated_lead_ids, self.lead_1 | dup_leads)

        convert.action_apply()
        self.assertEqual((self.lead_1 | dup_leads).exists(), opp_lost)


@tagged("lead_manage")
class TestLeadConvertBatch(crm_common.TestLeadConvertMassCommon):
    def test_initial_data(self):
        self.assertFalse(self.lead_1.date_conversion)
        self.assertEqual(
            self.lead_1.date_open, Datetime.from_string("2020-01-15 11:30:00")
        )
        self.assertEqual(self.lead_1.user_id, self.user_sales_leads)
        self.assertEqual(self.lead_1.team_id, self.sales_team_1)
        self.assertEqual(self.lead_1.stage_id, self.stage_team1_1)

        self.assertEqual(self.lead_w_partner.stage_id, self.env["crm.stage"])
        self.assertEqual(self.lead_w_partner.user_id, self.user_sales_manager)
        self.assertEqual(self.lead_w_partner.team_id, self.sales_team_1)

        self.assertEqual(self.lead_w_partner_company.stage_id, self.stage_team1_1)
        self.assertEqual(self.lead_w_partner_company.user_id, self.user_sales_manager)
        self.assertEqual(self.lead_w_partner_company.team_id, self.sales_team_1)

        self.assertEqual(self.lead_w_contact.stage_id, self.stage_gen_1)
        self.assertEqual(self.lead_w_contact.user_id, self.user_sales_salesman)
        self.assertEqual(self.lead_w_contact.team_id, self.sales_team_convert)

        self.assertEqual(self.lead_w_email.stage_id, self.stage_gen_1)
        self.assertEqual(self.lead_w_email.user_id, self.user_sales_salesman)
        self.assertEqual(self.lead_w_email.team_id, self.sales_team_convert)

        self.assertEqual(self.lead_w_email_lost.stage_id, self.stage_team1_2)
        self.assertEqual(self.lead_w_email_lost.user_id, self.user_sales_leads)
        self.assertEqual(self.lead_w_email_lost.team_id, self.sales_team_1)

    @users("user_sales_manager")
    def test_lead_convert_batch_internals(self):
        date = self.env.cr.now()

        lead_w_partner = self.lead_w_partner
        lead_w_contact = self.lead_w_contact
        lead_w_email_lost = self.lead_w_email_lost
        lead_w_email_lost.action_set_lost()
        self.assertEqual(lead_w_email_lost.active, False)

        convert = (
            self.env["crm.lead2opportunity.partner"]
            .with_context(
                {
                    "active_model": "crm.lead",
                    "active_id": self.lead_1.id,
                    "active_ids": (
                        self.lead_1
                        | lead_w_partner
                        | lead_w_contact
                        | lead_w_email_lost
                    ).ids,
                }
            )
            .create({})
        )

        self.assertEqual(convert.user_id, self.lead_1.user_id)
        self.assertEqual(convert.team_id, self.lead_1.team_id)
        self.assertFalse(convert.partner_id)
        self.assertEqual(convert.name, "convert")
        self.assertEqual(convert.action, "create")

        convert.action_apply()
        self.assertEqual(convert.user_id, self.user_sales_leads)
        self.assertEqual(convert.team_id, self.sales_team_1)
        self.assertFalse(lead_w_email_lost.active)
        self.assertFalse(lead_w_email_lost.date_conversion)
        self.assertEqual(lead_w_email_lost.partner_id, self.env["res.partner"])
        self.assertEqual(lead_w_email_lost.stage_id, self.stage_team1_2)
        for opp in self.lead_1 | lead_w_partner | lead_w_contact:
            self.assertEqual(opp.type, "opportunity")
            self.assertTrue(opp.active)
            self.assertEqual(opp.user_id, convert.user_id)
            self.assertEqual(opp.team_id, convert.team_id)
            if opp == self.lead_1:
                self.assertEqual(
                    opp.date_open, Datetime.from_string("2020-01-15 11:30:00")
                )
            else:
                self.assertEqual(opp.date_open, date)
            self.assertEqual(opp.date_conversion, date)
            if opp in (self.lead_1, lead_w_partner):
                self.assertEqual(opp.stage_id, self.stage_team1_1)
            elif opp == lead_w_contact:
                self.assertEqual(opp.stage_id, self.stage_gen_1)
            else:
                self.assertFalse(True)
