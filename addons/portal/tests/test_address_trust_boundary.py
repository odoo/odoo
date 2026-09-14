import logging

from odoo import Command
from odoo.http import Request
from odoo.tests import HttpCase, tagged

_logger = logging.getLogger(__name__)


@tagged("-at_install", "post_install")
class TestAddressTrustBoundary(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country = cls.env.ref("base.be")
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Trust Boundary Customer",
                "email": "trust.boundary@example.com",
                "phone_ids": [
                    Command.create({"number": "+32 456 00 00 00", "type": "landline"})
                ],
                "street": "Rue du Test 1",
                "city": "Bruxelles",
                "zip": "1000",
                "country_id": cls.country.id,
            }
        )
        cls.user = cls.env["res.users"].create(
            {
                "login": "trust_boundary",
                "password": "trust_boundary",
                "partner_id": cls.partner.id,
                "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
            }
        )
        cls.company_partner = cls.env["res.partner"].create(
            {"name": "Trust Boundary Co", "is_company": True, "vat": "BE0477472701"}
        )
        cls.partner.parent_id = cls.company_partner
        cls.sibling_address = cls.env["res.partner"].create(
            {
                "name": "Trust Boundary Billing",
                "parent_id": cls.company_partner.id,
                "type": "invoice",
                "email": "billing@example.com",
                "phone_ids": [
                    Command.create({"number": "+32 456 00 00 01", "type": "landline"})
                ],
                "street": "Rue du Test 2",
                "city": "Bruxelles",
                "zip": "1000",
                "country_id": cls.country.id,
            }
        )

    def _submit(self, **form_data):
        self.authenticate("trust_boundary", "trust_boundary")
        payload = {
            "partner_id": str(self.partner.id),
            "address_type": "billing",
            "use_delivery_as_billing": "true",
            "required_fields": "name,email",
            **form_data,
        }
        response = self.url_open(
            "/my/address/submit",
            data={**payload, "csrf_token": Request.csrf_token(self)},
        )
        response.raise_for_status()
        return response.json()

    def test_validation_runs_by_default(self):
        feedback = self._submit(name="", email="")

        self.assertNotIn("redirectUrl", feedback)
        self.assertIn("name", feedback["invalid_fields"])
        self.assertIn("email", feedback["invalid_fields"])
        self.partner.invalidate_recordset()
        self.assertEqual(self.partner.name, "Trust Boundary Customer")

    def test_verify_address_values_is_not_client_settable(self):
        for hostile_value in ("", "0", "false", "False"):
            with self.subTest(verify_address_values=hostile_value):
                feedback = self._submit(
                    name="", email="", verify_address_values=hostile_value
                )

                self.assertNotIn(
                    "redirectUrl",
                    feedback,
                    "validation was skipped: the address was accepted",
                )
                self.assertIn("name", feedback["invalid_fields"])
                self.partner.invalidate_recordset()
                self.assertEqual(
                    self.partner.name,
                    "Trust Boundary Customer",
                    "an unvalidated write reached the database",
                )

    def test_email_format_still_checked_under_hostile_flag(self):
        feedback = self._submit(
            name="Trust Boundary Customer",
            email="not-an-email",
            phone="+32 456 00 00 00",
            street="Rue du Test 1",
            city="Bruxelles",
            zip="1000",
            country_id=str(self.country.id),
            verify_address_values="",
        )

        self.assertIn("email", feedback["invalid_fields"])
        self.partner.invalidate_recordset()
        self.assertEqual(self.partner.email, "trust.boundary@example.com")

    def test_bypass_cannot_reach_the_shared_company_record(self):
        self.authenticate("trust_boundary", "trust_boundary")
        response = self.url_open(
            "/my/address/submit",
            data={
                "partner_id": str(self.sibling_address.id),
                "address_type": "billing",
                "use_delivery_as_billing": "true",
                "required_fields": "name,email",
                "name": "Trust Boundary Billing",
                "email": "billing@example.com",
                "phone": "+32 456 00 00 01",
                "street": "Rue du Test 2",
                "city": "Bruxelles",
                "zip": "1000",
                "country_id": str(self.country.id),
                "company_name": "PWNED COMPANY",
                "vat": "BE0000000097",
                "verify_address_values": "",
                "csrf_token": Request.csrf_token(self),
            },
        )
        response.raise_for_status()

        self.company_partner.invalidate_recordset()
        self.sibling_address.invalidate_recordset()
        self.assertEqual(
            self.company_partner.name,
            "Trust Boundary Co",
            "a sub-address submission renamed the shared company record",
        )
        self.assertEqual(
            self.company_partner.vat,
            "BE0477472701",
            "a sub-address submission rewrote the company VAT",
        )

    def test_callback_cannot_leave_the_origin(self):
        valid_address = {
            "name": "Trust Boundary Customer",
            "email": "trust.boundary@example.com",
            "phone": "+32 456 00 00 00",
            "street": "Rue du Test 1",
            "city": "Bruxelles",
            "zip": "1000",
            "country_id": str(self.country.id),
        }
        for hostile_url in (
            "https://evil.example/phish",
            "//evil.example/phish",
            "http://evil.example",
            "/\\evil.example",
            "javascript:alert(1)",
        ):
            with self.subTest(callback=hostile_url):
                feedback = self._submit(**valid_address, callback=hostile_url)

                self.assertEqual(feedback.get("redirectUrl"), "/my/addresses")

    def test_valid_sub_address_cannot_rename_company(self):
        self._assert_sub_address_cannot_rename_company(str(self.sibling_address.id))
        self.sibling_address.invalidate_recordset()
        self.assertEqual(self.sibling_address.name, "Billing address")

    def test_new_sub_address_cannot_rename_company(self):
        before = self.company_partner.child_ids
        self._assert_sub_address_cannot_rename_company("")
        self.company_partner.invalidate_recordset()
        created = self.company_partner.child_ids - before
        self.assertEqual(len(created), 1)
        self.assertEqual(created.name, "Billing address")

    def _assert_sub_address_cannot_rename_company(self, partner_id):
        feedback = self._submit(
            partner_id=partner_id,
            name="Billing address",
            email="billing@example.com",
            phone="+32 456 00 00 01",
            street="Rue du Test 2",
            city="Bruxelles",
            zip="1000",
            country_id=str(self.country.id),
            company_name="Unauthorized company rename",
        )
        self.assertIn("redirectUrl", feedback)
        self.company_partner.invalidate_recordset()
        _logger.debug(
            "Address %s submission left company name %r",
            partner_id,
            self.company_partner.name,
        )
        self.assertEqual(self.company_partner.name, "Trust Boundary Co")

    def test_main_address_can_update_company_name(self):
        feedback = self._submit(
            name=self.partner.name,
            email=self.partner.email,
            phone="+32 456 00 00 00",
            street=self.partner.street,
            city=self.partner.city,
            zip=self.partner.zip,
            country_id=str(self.country.id),
            company_name="Updated company name",
        )
        self.assertIn("redirectUrl", feedback)
        self.company_partner.invalidate_recordset()
        self.assertEqual(self.company_partner.name, "Updated company name")

    def test_callback_keeps_local_paths(self):
        feedback = self._submit(
            name="Trust Boundary Customer",
            email="trust.boundary@example.com",
            phone="+32 456 00 00 00",
            street="Rue du Test 1",
            city="Bruxelles",
            zip="1000",
            country_id=str(self.country.id),
            callback="/my/orders?page=2",
        )

        self.assertEqual(feedback.get("redirectUrl"), "/my/orders?page=2")

    def test_account_page_never_renders_an_offsite_discard_link(self):
        self.authenticate("trust_boundary", "trust_boundary")
        for hostile_url in ("https://evil.example/phish", "//evil.example/phish"):
            with self.subTest(redirect=hostile_url):
                body = self.url_open(
                    "/my/account", params={"redirect": hostile_url}
                ).text

                self.assertNotIn("evil.example", body)

    def test_account_page_keeps_a_local_discard_link(self):
        self.authenticate("trust_boundary", "trust_boundary")
        body = self.url_open("/my/account", params={"redirect": "/my/addresses"}).text

        self.assertIn('name="callback" value="/my/addresses"', body)
