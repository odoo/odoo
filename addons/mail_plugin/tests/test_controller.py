import json
from unittest.mock import Mock, patch

from odoo.exceptions import AccessError

from odoo.addons.iap.tools import iap_tools
from odoo.addons.mail_plugin.tests.common import (
    TestMailPluginControllerCommon,
    as_outlook_user,
)


class TestMailPluginController(TestMailPluginControllerCommon):
    def test_enrich_and_create_company(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Test partner",
                "email": "test@test_domain.xyz",
                "is_company": False,
            }
        )

        result = self.mock_enrich_and_create_company(
            partner.id,
            lambda _, domain: {"return": domain},
        )

        self.assertEqual(result["enrichment_info"], {"type": "company_created"})
        self.assertEqual(
            result["company"]["additionalInfo"]["return"], "test_domain.xyz"
        )

        company_id = result["company"]["id"]
        company = self.env["res.partner"].browse(company_id)
        partner.invalidate_recordset()
        self.assertEqual(
            partner.parent_id, company, "Should change the company of the partner"
        )

    @as_outlook_user("employee")
    def test_get_partner_blacklisted_domain(self):
        domain = min(iap_tools._MAIL_PROVIDERS)

        data = {
            "id": 0,
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"email": "contact@" + domain, "name": "test"},
        }

        mocked_request_enrich = Mock()

        with patch(
            "odoo.addons.iap.models.iap_enrich_api.IapEnrichApi._request_enrich",
            new=mocked_request_enrich,
        ):
            result = (
                self.url_open(
                    "/mail_plugin/partner/get",
                    data=json.dumps(data).encode(),
                    headers={"Content-Type": "application/json"},
                )
                .json()
                .get("result", {})
            )

        self.assertFalse(mocked_request_enrich.called)
        self.assertEqual(result["partner"]["enrichment_info"]["type"], "missing_data")

    def test_get_partner_company_found(self):
        company = self.env["res.partner"].create(
            {
                "name": "Test partner",
                "email": "test@test_domain.xyz",
                "is_company": True,
            }
        )

        mock_iap_enrich = Mock()
        result = self.mock_plugin_partner_get(
            "Test", "qsd@test_domain.xyz", mock_iap_enrich
        )

        self.assertFalse(mock_iap_enrich.called)
        self.assertEqual(result["partner"]["id"], -1)
        self.assertEqual(result["partner"]["email"], "qsd@test_domain.xyz")
        self.assertEqual(result["partner"]["company"]["id"], company.id)
        self.assertFalse(result["partner"]["company"]["additionalInfo"])

    def test_get_partner_company_not_found(self):
        self.env["res.partner"].create(
            {
                "name": "Test partner",
                "email": "test@test_domain.xyz",
                "is_company": False,
            }
        )

        result = self.mock_plugin_partner_get(
            "Test",
            "qsd@test_domain.xyz",
            lambda _, domain: {"enrichment_info": "missing_data"},
        )

        self.assertEqual(result["partner"]["id"], -1)
        self.assertEqual(result["partner"]["email"], "qsd@test_domain.xyz")
        self.assertEqual(result["partner"]["company"]["id"], -1)

    def test_get_partner_iap_return_different_domain(self):
        result = self.mock_plugin_partner_get(
            "Test",
            "qsd@test_domain.xyz",
            lambda _, domain: {
                "name": "Name",
                "email": ["contact@gmail.com"],
                "iap_information": "test",
            },
        )

        first_company_id = result["partner"]["company"]["id"]
        first_company = self.env["res.partner"].browse(first_company_id)

        self.assertEqual(result["partner"]["id"], -1)
        self.assertEqual(result["partner"]["email"], "qsd@test_domain.xyz")
        self.assertTrue(first_company_id, "Should have created the company")
        self.assertEqual(
            result["partner"]["company"]["additionalInfo"]["iap_information"], "test"
        )

        self.assertEqual(first_company.name, "Name")
        self.assertEqual(first_company.email, "contact@gmail.com")

        mock_iap_enrich = Mock()
        result = self.mock_plugin_partner_get(
            "Test", "qsd@test_domain.xyz", mock_iap_enrich
        )
        self.assertFalse(
            mock_iap_enrich.called,
            "We already enriched this company, should not call IAP a second time",
        )

        second_company_id = result["partner"]["company"]["id"]
        self.assertEqual(
            first_company_id, second_company_id, "Should not create a new company"
        )
        self.assertEqual(
            result["partner"]["company"]["additionalInfo"]["iap_information"], "test"
        )

    def test_get_partner_no_access(self):
        partner = self.env["res.partner"].create(
            {"name": "Test", "website": "https://test.example.com"}
        )
        partner_count = self.env["res.partner"].search_count([])
        self.env["res.partner.iap"].create(
            {
                "partner_id": partner.id,
                "iap_search_domain": "@test.example.com",
            }
        )

        result = self.mock_plugin_partner_get(
            "Test",
            "test@test.example.com",
            lambda _, domain: {"name": "Name", "email": "test@test.example.com"},
        )
        self.assertEqual(
            result["partner"]["company"]["website"], "https://test.example.com"
        )
        new_partner_count = self.env["res.partner"].search_count([])
        self.assertEqual(
            new_partner_count, partner_count, "Should not have created a new partner"
        )

        def _check_access(record, operation):
            if operation == "read" and record == partner:
                return record, lambda: AccessError("No Access")
            return None

        with patch.object(type(partner), "_check_access", _check_access):
            result = self.mock_plugin_partner_get(
                "Test",
                "test@test.example.com",
                lambda _, domain: {"name": "Name", "email": "test@test.example.com"},
            )
        self.assertEqual(result["partner"]["company"].get("id"), partner.id)
        self.assertEqual(result["partner"]["company"].get("name"), "No Access")
        self.assertFalse(result["partner"]["company"].get("website"))
        new_partner_count = self.env["res.partner"].search_count([])
        self.assertEqual(
            new_partner_count, partner_count, "Should not have created a new partner"
        )

    def test_get_partner_no_email_returned_by_iap(self):
        result = self.mock_plugin_partner_get(
            "Test",
            "qsd@domain.com",
            lambda _, domain: {"name": "Name", "email": []},
        )

        first_company_id = result["partner"]["company"]["id"]
        self.assertTrue(first_company_id and first_company_id > 0)

        first_company = self.env["res.partner"].browse(first_company_id)
        self.assertEqual(first_company.name, "Name")
        self.assertFalse(first_company.email)

        result = self.mock_plugin_partner_get(
            "Test",
            "qsd@domain.com",
            lambda _, domain: {"name": "Name", "email": ["contact@" + domain]},
        )
        second_company_id = result["partner"]["company"]["id"]
        self.assertEqual(
            first_company_id, second_company_id, "Should not create a new company"
        )

    def test_get_partner_is_default_from(self):
        self.env["mail.alias.domain"].create(
            {"name": "example.com", "default_from": "notification"}
        )
        mock_iap_enrich = Mock()
        result = self.mock_plugin_partner_get(
            "Test partner", "notificaTION@EXAMPLE.COM", mock_iap_enrich
        )
        self.assertEqual(
            result,
            {
                "partner": {
                    "name": "Notification",
                    "email": "notification@example.com",
                    "enrichment_info": {
                        "type": "odoo_custom_error",
                        "info": "This is your notification address. Search the Contact manually to link this email to a record.",
                    },
                },
            },
        )
