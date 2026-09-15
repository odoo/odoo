from psycopg import IntegrityError

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResourceParty(TransactionCase):
    """A human resource follows its party's name and timezone; a material one
    keeps its own."""

    def test_a_resource_with_a_party_reads_the_party(self):
        partner = self.env["res.partner"].create(
            {"name": "Party One", "tz": "Asia/Tokyo"}
        )
        resource = self.env["resource.resource"].create(
            {"name": "ignored", "partner_id": partner.id}
        )
        self.assertEqual(resource.name, "Party One")
        self.assertEqual(resource.tz, "Asia/Tokyo")
        partner.write({"name": "Party Renamed", "tz": "Europe/Paris"})
        self.assertEqual(resource.name, "Party Renamed")
        self.assertEqual(resource.tz, "Europe/Paris")

    def test_writing_the_resource_writes_the_party(self):
        partner = self.env["res.partner"].create({"name": "Party Two", "tz": "UTC"})
        resource = self.env["resource.resource"].create({"partner_id": partner.id})
        resource.write({"name": "Party Two Edited", "tz": "America/Lima"})
        self.assertEqual(partner.name, "Party Two Edited")
        self.assertEqual(partner.tz, "America/Lima")

    def test_a_material_resource_keeps_its_own(self):
        resource = self.env["resource.resource"].create(
            {"name": "Lathe", "resource_type": "material", "tz": "Europe/Brussels"}
        )
        resource.name = "Lathe 2"
        self.assertEqual(resource.name, "Lathe 2")
        self.assertEqual(resource.tz, "Europe/Brussels")
        self.assertFalse(resource.partner_id)

    def test_a_party_without_timezone_leaves_the_resource_its_own(self):
        partner = self.env["res.partner"].create({"name": "No TZ"})
        partner.tz = False
        resource = self.env["resource.resource"].create(
            {"partner_id": partner.id, "tz": "Pacific/Apia"}
        )
        self.assertEqual(resource.tz, "Pacific/Apia")

    def test_a_human_resource_without_a_party_becomes_one(self):
        resource = self.env["resource.resource"].create(
            {"name": "Walk-in Contractor", "tz": "America/Mexico_City"}
        )
        self.assertTrue(resource.partner_id)
        self.assertEqual(resource.partner_id.name, "Walk-in Contractor")
        self.assertEqual(resource.partner_id.tz, "America/Mexico_City")

    def test_a_users_resource_is_the_users_party(self):
        user = self.env["res.users"].create(
            {"name": "Resource User", "login": "resource_party_user"}
        )
        resource = self.env["resource.resource"].create(
            {"name": "ignored", "user_id": user.id}
        )
        self.assertEqual(resource.partner_id, user.partner_id)

    def test_a_person_is_one_human_resource_per_company(self):
        partner = self.env["res.partner"].create({"name": "Only Once"})
        self.env["resource.resource"].create({"partner_id": partner.id})
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env["resource.resource"].create({"partner_id": partner.id})
        other_company = self.env["res.company"].create({"name": "Second Employer"})
        elsewhere = self.env["resource.resource"].create(
            {"partner_id": partner.id, "company_id": other_company.id}
        )
        self.assertEqual(elsewhere.partner_id, partner)

    def test_a_human_resource_cannot_drop_its_party(self):
        resource = self.env["resource.resource"].create({"name": "Keeps Party"})
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            resource.partner_id = False
            resource.flush_recordset()

    def test_a_copied_human_resource_is_a_new_person(self):
        resource = self.env["resource.resource"].create({"name": "Original"})
        copy = resource.copy()
        self.assertTrue(copy.partner_id)
        self.assertNotEqual(copy.partner_id, resource.partner_id)
        self.assertEqual(copy.name, "Original (copy)")

    def test_get_or_create_resources_reuses_and_creates_in_order(self):
        company = self.env.company
        held, archived, fresh = self.env["res.partner"].create(
            [{"name": "Holds One"}, {"name": "Archived One"}, {"name": "Has None"}]
        )
        existing = self.env["resource.resource"].create(
            [
                {"partner_id": held.id, "company_id": company.id},
                {"partner_id": archived.id, "company_id": company.id, "active": False},
            ]
        )
        resources = (fresh | held | archived)._get_or_create_resources(company)
        self.assertEqual(len(resources), 3)
        self.assertEqual(resources[1:], existing)
        self.assertEqual(resources[0].partner_id, fresh)
        self.assertEqual(resources[0].resource_type, "user")
        self.assertEqual(resources[0].company_id, company)
        self.assertEqual(
            (fresh | held | archived)._get_or_create_resources(company), resources
        )

    def test_a_derived_timezone_never_reaches_the_party(self):
        user = self.env["res.users"].create(
            {"name": "Zoneless User", "login": "zoneless_user"}
        )
        user.partner_id.tz = False
        calendar = self.env["resource.calendar"].create(
            {"name": "Tokyo Hours", "tz": "Asia/Tokyo"}
        )
        resource = self.env["resource.resource"].create(
            {"name": "ignored", "user_id": user.id, "calendar_id": calendar.id}
        )
        self.assertEqual(resource.tz, "Asia/Tokyo")
        self.assertFalse(user.partner_id.tz)
        resource.tz = "Europe/Madrid"
        self.assertEqual(user.partner_id.tz, "Europe/Madrid")
