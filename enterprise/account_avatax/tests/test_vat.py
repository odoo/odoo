from odoo.tests.common import tagged
from .common import TestAccountAvataxCommon


@tagged("-at_install", "post_install")
class TestAccountAvalaraVAT(TestAccountAvataxCommon):
    """https://developer.avalara.com/certification/avatax/VAT-badge/"""

    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()
        cls.shipping_partner = cls.partner.copy({
            'name': 'Delivery Partner',
            'street': '1000 Market St',
        })
        cls.partner.vat = 'businessid'
        cls.product = cls.env["product.product"].create({
            'name': "Product",
            'list_price': 15.00,
            'standard_price': 15.00,
            'supplier_taxes_id': None,
            'avatax_category_id': cls.env.ref('account_avatax.DC010000').id,
        })
        with cls._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            cls.invoice = cls.env['account.move'].create({
                'partner_id': cls.partner.id,
                'partner_shipping_id': cls.shipping_partner.id,
                'fiscal_position_id': cls.fp_avatax.id,
                'invoice_date': '2021-01-01',
                'move_type': 'out_invoice',
                'invoice_line_ids': [
                    (0, 0, {
                        'product_id': cls.product.id,
                        'price_unit': cls.product.list_price,
                    }),
                ]
            })
            cls.invoice.button_external_tax_calculation()
        cls.captured_arguments = capture.val['json']['createTransactionModel']
        return res

    def test_business_id(self):
        """Also known as VAT Registration ID

        This data element should be found directly on the transaction (sales order, sales invoice)
        header. Some applications may not carry that information onto the transaction itself, and
        the connector may have to pull directly from the customer record.
        """
        vat = self.captured_arguments['businessIdentificationNo']
        self.assertEqual(vat, 'businessid')

    def test_country_code(self):
        """The country code associated with the various addresses stored on the transaction must be
        sent.

        This information should not have to be sourced from the customer record.
        """
        self.assertTrue(all(
            all(address.get('country'))
            for address in self.captured_arguments['addresses'].values()
        ))

    def test_currency_code(self):
        """Transaction currency code

        AvaTax needs to know the currency the document is transacted in, not the default currency
        information.
        """
        currency_code = self.captured_arguments['currencyCode']
        self.assertEqual(currency_code, 'USD')

    def test_ship_to_address(self):
        """Ship-to address must contain country code and use the shipping partner."""
        destination_address = self.captured_arguments['addresses']['shipTo']
        self.assertEqual(destination_address, {
            'city': 'San Francisco',
            'country': 'US',
            'line1': '1000 Market St',
            'postalCode': '94114',
            'region': 'CA',
        })

    def test_ship_from_address(self):
        """Ship-from address must include country code."""
        country_code = self.captured_arguments['addresses']['shipFrom']['country']
        self.assertEqual(country_code, 'US')
