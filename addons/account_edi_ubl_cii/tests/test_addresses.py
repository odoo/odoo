from odoo.tests import tagged

from odoo.addons.portal.tests.test_addresses import TestPortalAddresses


@tagged('post_install', '-at_install')
class TestAddresses(TestPortalAddresses):
    def test_portal_address_invoice_edi_format_with_company(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        csrf_token = self.csrf_token()
        portal_partner = self.portal_user.partner_id

        self._submit_address_values({
            **self.default_address_values,
            "csrf_token": csrf_token,
            "parent_name": "Test Company",
        })

        # Now set invoice_edi_format
        self._submit_address_values({
            **self.default_address_values,
            "csrf_token": csrf_token,
            "invoice_edi_format": "facturx",
        })

        self.assertEqual(portal_partner.invoice_edi_format, "facturx")
