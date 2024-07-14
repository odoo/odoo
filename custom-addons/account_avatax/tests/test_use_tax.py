from odoo.tests.common import tagged
from .common import TestAvataxCommon, TestAccountAvataxCommon


@tagged("-at_install", "post_install")
class TestAccountAvalaraUseTaxVendorManagement(TestAvataxCommon):
    """https://developer.avalara.com/certification/avatax/use-tax-badge/"""
    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()
        cls.config = cls.env['res.config.settings'].create({})
        return res

    def test_vendor_identifier_mapping(self):
        """Identify the vendor identifier field (typically the database key in the vendor master)
        to map to the “CustomerCode” field in Avalara."""
        Partner = self.env['res.partner']
        partner = Partner.search([], limit=1)
        partner_via_code = Partner.search([('avatax_unique_code', '=', partner.avatax_unique_code)], limit=1)
        self.assertEqual(partner, partner_via_code, "Couldn't find partner via unique avatax code")


@tagged("-at_install", "post_install")
class TestAccountAvalaraUseTaxProductManagement(TestAccountAvataxCommon):
    """https://developer.avalara.com/certification/avatax/use-tax-badge/"""

    def test_item_code(self):
        """Identify item/service/charge code (number, ID) to pass to the AvaTax service. If the
        customer has access to UPC, they should be able to prepend UPC to the code and have it come
        across in the item code field. If there is no UPC, it should fall back to SKU. (See UPC
        requirements in the Administration & Utilities Integration section) For Purchase Invoices
        not associated with a Purchase Order, you may not have access to the ItemCode from the
        client application. In that case, simply use the GL account number/cost center identifier.
        """
        self.env.company.avalara_use_upc = False
        with self._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            invoice = self._create_invoice()
            invoice.button_external_tax_calculation()
        self.assertEqual(capture.val['json']['createTransactionModel']['lines'][0]['itemCode'], 'PROD1')

        self.env.company.avalara_use_upc = True
        with self._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            invoice = self._create_invoice()
            invoice.button_external_tax_calculation()
        self.assertEqual(capture.val['json']['createTransactionModel']['lines'][0]['itemCode'], 'UPC:123456789')

    def test_item_description(self):
        """Identify item/service/charge description to pass to the AvaTax service with a
        human-readable description or item name.
        """
        with self._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            invoice = self._create_invoice()
            invoice.button_external_tax_calculation()
        line_description = capture.val['json']['createTransactionModel']['lines'][0]['description']
        self.assertEqual(invoice.invoice_line_ids.name, line_description)
