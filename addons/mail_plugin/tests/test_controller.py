# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.iap.tests.common import MockIAPEnrich
from odoo.addons.mail_plugin.tests.common import TestMailPluginControllerCommon


class TestMailPluginController(TestMailPluginControllerCommon, MockIAPEnrich):

    def test_enrich_and_create_company(self):
        partner = self.env["res.partner"].create({
            "name": "Test partner",
            "email": "test@test_domain.com",
            "is_company": False,
        })

        with self.mockIAPEnrichGateway(name_list=["Test"]):
            result = self.mock_enrich_and_create_company(partner.id)

        self.assertEqual(result["enrichment_info"], {"type": "company_created"})
        self.assertEqual(result["company"]["additionalInfo"]["clearbit_id"], "123_ClearbitID_Test")

        company = self.env["res.partner"].browse(result["company"]["id"])
        partner.invalidate_cache()
        self.assertEqual(partner.parent_id, company, "Should change the company of the partner")

    def test_get_partner_blacklisted_domain(self):
        """Test enrichment on a blacklisted domain.

        Even is the domain is blacklisted, we should not duplicate the company each
        time a request is made.
        """
        blacklist_domain = "gmail.com"
        email = "qsd@%s" % blacklist_domain

        with self.mockIAPEnrichGateway(name_list=["Test"], email_data={blacklist_domain: {"email": [email]}}):
            result = self.mock_plugin_partner_get("Test", email)

        self.assertEqual(result['partner']['id'], -1)
        first_company_id = result["partner"]["company"]["id"]
        self.assertTrue(first_company_id and first_company_id > 0)
        first_company = self.env["res.partner"].browse(first_company_id)

        self.assertEqual(result["partner"]["enrichment_info"], {"type": "company_created"})
        self.assertEqual(result["partner"]["company"]["additionalInfo"]["clearbit_id"], "123_ClearbitID_Test")
        self.assertEqual(first_company.name, "Test GmbH")
        self.assertEqual(first_company.email, email)

        # Test that we do not duplicate the company and that we return the previous one
        with self.mockIAPEnrichGateway(name_list=["Test"], email_data={blacklist_domain: {"email": [email]}}):
            result = self.mock_plugin_partner_get("Test", email)

        self.assertFalse(
            self._contact_iap_mock.called,
            "We already enriched this company, should not call IAP a second time")
        self.assertEqual(result['partner']['id'], first_company_id)
        self.assertEqual(result["partner"]["company"]["id"], first_company_id, "Should not create a new company")

        # But the same blacklisted domain on a different local part
        # should create a new company (e.g.: asbl_XXXX@gmail.com VS asbl_YYYY@gmail.com)
        email2 = "asbl@%s" % blacklist_domain
        with self.mockIAPEnrichGateway(name_list=["Test"], email_data={blacklist_domain: {"email": [email2]}}):
            result = self.mock_plugin_partner_get("Test", email2)

        self.assertTrue(self._contact_iap_mock.called)
        self.assertEqual(result['partner']['id'], -1)
        second_company_id = result["partner"]["company"]["id"]
        self.assertTrue(first_company_id and first_company_id > 0)
        second_company = self.env["res.partner"].browse(second_company_id)
        self.assertTrue(first_company != second_company, "Should create a new company")
        self.assertEqual(second_company.name, "Test GmbH")
        self.assertEqual(second_company.email, email2)

    def test_get_partner_company_found(self):
        company = self.env["res.partner"].create({
            "name": "Test partner",
            "email": "test@test_domain.com",
            "is_company": True,
        })

        with self.mockIAPEnrichGateway(name_list=["Test"],
                                       email_data={"test_domain.com": {"email": ["test@test_domain.com"]}}):
            result = self.mock_plugin_partner_get("Test", "test@test_domain.com")

        self.assertFalse(self._contact_iap_mock.called)
        self.assertEqual(result["partner"]["id"], company.id)
        self.assertEqual(result["partner"]["email"], "test@test_domain.com")
        self.assertEqual(result["partner"]["company"]["id"], company.id)
        self.assertFalse(result["partner"]["company"]["additionalInfo"])

    def test_get_partner_company_not_found(self):
        partner = self.env["res.partner"].create({
            "name": "Test partner",
            "email": "test@test_domain.com",
            "is_company": False,
        })

        with self.mockIAPEnrichGateway(name_list=["Test"],
                                       email_data={"test_domain.com": {"email": ["test@test_domain.com"]}}):
            result = self.mock_plugin_partner_get("Test", "test@test_domain.com")

        self.assertFalse(self._contact_iap_mock.called)
        self.assertEqual(result["partner"]["id"], partner.id)
        self.assertEqual(result["partner"]["email"], "test@test_domain.com")
        self.assertEqual(result["partner"]["company"]["id"], -1)

    def test_get_partner_iap_return_different_domain(self):
        """ Test the case where the domain of the email returned by IAP is not the
        same as the domain requested. """
        with self.mockIAPEnrichGateway(name_list=["Test"],
                                       email_data={"test_domain.com": {"email": ["contact@gmail.com"]}}):
            result = self.mock_plugin_partner_get("Test", "test@test_domain.com")

        self.assertEqual(result["partner"]["enrichment_info"], {'type': 'company_created'})
        self.assertTrue(result["partner"]["company"]["id"] > 0)
        self.assertEqual(result["partner"]["id"], -1)
        self.assertEqual(result["partner"]["email"], "test@test_domain.com")
        first_company = self.env["res.partner"].browse(result["partner"]["company"]["id"])
        self.assertEqual(first_company.name, "Test GmbH")
        self.assertEqual(first_company.email, "contact@gmail.com")

        # Test that we do not duplicate the company and that we return the previous one
        with self.mockIAPEnrichGateway(name_list=["Test"],
                                       email_data={"test_domain.com": {"email": ["contact@gmail.com"]}}):
            result = self.mock_plugin_partner_get("Test", "test@test_domain.com")

        self.assertFalse(self._contact_iap_mock.called, "We already enriched this company, should not call IAP a second time")
        self.assertEqual(result["partner"]["company"]["id"], first_company.id, "Should not create a new company")

    def test_get_partner_no_email_returned_by_iap(self):
        """Test the case where IAP do not return an email address. We should not
        duplicate the previously enriched company and we should be able to retrieve
        the first one. """
        with self.mockIAPEnrichGateway(name_list=["Test"],
                                       email_data={"test_domain.com": {"email": []}}):
            result = self.mock_plugin_partner_get("Test", "test@test_domain.com")

        self.assertEqual(result["partner"]["enrichment_info"], {'type': 'company_created'})
        self.assertTrue(result["partner"]["company"]["id"] > 0)
        first_company = self.env["res.partner"].browse(result["partner"]["company"]["id"])
        self.assertEqual(first_company.name, "Test GmbH")
        self.assertFalse(first_company.email)

        # Test that we do not duplicate the company and that we return the previous one
        with self.mockIAPEnrichGateway(name_list=["Test"],
                                       email_data={"test_domain.com": {"email": ["contact#test_domain.com"]}}):
            result = self.mock_plugin_partner_get("Test", "test@test_domain.com")

        self.assertFalse(self._contact_iap_mock.called)
        self.assertEqual(result["partner"]["enrichment_info"], None)
        self.assertEqual(result["partner"]["company"]["id"], first_company.id, "Should not create a new company")
