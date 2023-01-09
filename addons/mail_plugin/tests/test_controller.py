# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import Mock, patch

from odoo.addons.iap.tools import iap_tools
from odoo.addons.mail_plugin.tests.common import TestMailPluginControllerCommon, mock_auth_method_outlook


class TestMailPluginController(TestMailPluginControllerCommon):

    def test_enrich_and_create_company(self):
        partner = self.env["res.partner"].create({
            "name": "Test partner",
            "email": "test@test_domain.xyz",
            "is_company": False,
        })

        result = self.mock_enrich_and_create_company(
            partner.id,
            lambda _, domain: {"return": domain},
        )

        self.assertEqual(result["enrichment_info"], {"type": "company_created"})
        self.assertEqual(result["company"]["additionalInfo"]["return"], "test_domain.xyz")

        company_id = result["company"]["id"]
        company = self.env["res.partner"].browse(company_id)
        partner.invalidate_recordset()
        self.assertEqual(partner.parent_id, company, "Should change the company of the partner")

    @mock_auth_method_outlook('employee')
    def test_get_partner_blacklisted_domain(self):
        """Test enrichment on a blacklisted domain, should return an error."""
        domain = list(iap_tools._MAIL_DOMAIN_BLACKLIST)[0]

        data = {
            "id": 0,
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"email": "contact@" + domain, "name": "test"},
        }

        mocked_request_enrich = Mock()

        with patch(
            "odoo.addons.iap.models.iap_enrich_api.IapEnrichAPI"
            "._request_enrich",
            new=mocked_request_enrich,
        ):
            result = self.url_open(
                "/mail_plugin/partner/get",
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
            ).json().get("result", {})

        self.assertFalse(mocked_request_enrich.called)
        self.assertEqual(result['partner']['enrichment_info']['type'], 'missing_data')

    def test_get_partner_company_found(self):
        company = self.env["res.partner"].create({
            "name": "Test partner",
            "email": "test@test_domain.xyz",
            "is_company": True,
        })

        mock_iap_enrich = Mock()
        result = self.mock_plugin_partner_get("Test", "qsd@test_domain.xyz", mock_iap_enrich)

        self.assertFalse(mock_iap_enrich.called)
        self.assertEqual(result["partner"]["id"], -1)
        self.assertEqual(result["partner"]["email"], "qsd@test_domain.xyz")
        self.assertEqual(result["partner"]["company"]["id"], company.id)
        self.assertFalse(result["partner"]["company"]["additionalInfo"])

    def test_get_partner_company_not_found(self):
        self.env["res.partner"].create({
            "name": "Test partner",
            "email": "test@test_domain.xyz",
            "is_company": False,
        })

        result = self.mock_plugin_partner_get(
            "Test",
            "qsd@test_domain.xyz",
            lambda _, domain: {"enrichment_info": "missing_data"},
        )

        self.assertEqual(result["partner"]["id"], -1)
        self.assertEqual(result["partner"]["email"], "qsd@test_domain.xyz")
        self.assertEqual(result["partner"]["company"]["id"], -1)

    def test_get_partner_iap_return_different_domain(self):
        """
        Test the case where the domain of the email returned by IAP is not the same as
        the domain requested.
        """
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
        self.assertEqual(result["partner"]["company"]["additionalInfo"]["iap_information"], "test")

        self.assertEqual(first_company.name, "Name")
        self.assertEqual(first_company.email, "contact@gmail.com")

        # Test that we do not duplicate the company and that we return the previous one
        mock_iap_enrich = Mock()
        result = self.mock_plugin_partner_get("Test", "qsd@test_domain.xyz", mock_iap_enrich)
        self.assertFalse(mock_iap_enrich.called, "We already enriched this company, should not call IAP a second time")

        second_company_id = result["partner"]["company"]["id"]
        self.assertEqual(first_company_id, second_company_id, "Should not create a new company")
        self.assertEqual(result["partner"]["company"]["additionalInfo"]["iap_information"], "test")

    def test_get_partner_no_email_returned_by_iap(self):
        """Test the case where IAP do not return an email address.

        We should not duplicate the previously enriched company and we should be able to
        retrieve the first one.
        """
        result = self.mock_plugin_partner_get(
            "Test", "qsd@domain.com",
            lambda _, domain: {"name": "Name", "email": []},
        )

        first_company_id = result["partner"]["company"]["id"]
        self.assertTrue(first_company_id and first_company_id > 0)

        first_company = self.env["res.partner"].browse(first_company_id)
        self.assertEqual(first_company.name, "Name")
        self.assertFalse(first_company.email)

        # Test that we do not duplicate the company and that we return the previous one
        result = self.mock_plugin_partner_get(
            "Test", "qsd@domain.com",
            lambda _, domain: {"name": "Name", "email": ["contact@" + domain]},
        )
        second_company_id = result["partner"]["company"]["id"]
        self.assertEqual(first_company_id, second_company_id, "Should not create a new company")
