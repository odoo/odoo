from datetime import datetime

from odoo.addons.l10n_ar.tests.common import TestAr
from odoo.addons.website_sale.tests.common import MockRequest
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nArWebsiteSale(TestAr):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Set up Argentina-specific test company and website
        cls.ar_company = cls.company_data['company']
        cls.ar_website = cls.env['website'].create({
            'name': 'AR Website',
            'company_id': cls.ar_company.id,
        })

        # Create a base product template with default tax
        cls.product_1 = cls.env['product.template'].create({
            'name': 'Product 1',
            'is_published': True,
            'list_price': 1000,
            'taxes_id': cls.env['account.chart.template'].ref('ri_tax_vat_21_ventas'),
        })

        # Create color attribute and values
        cls.color_attribute = cls.env['product.attribute'].create({
            'name': 'Color',
            'display_type': 'color',
        })
        cls.color_white = cls.env['product.attribute.value'].create({
            'name': 'White',
            'html_color': '#FFFFFF',
            'attribute_id': cls.color_attribute.id,
        })
        cls.color_black = cls.env['product.attribute.value'].create({
            'name': 'Black',
            'html_color': '#000000',
            'attribute_id': cls.color_attribute.id,
        })

    def assertDictContains(self, actual_dict, expected_subset):
        """Assert that actual_dict contains all key-value pairs from expected_subset."""
        for key, expected_value in expected_subset.items():
            self.assertEqual(actual_dict.get(key), expected_value)

    def _get_combination_info(self, product_id=None, quantity=1):
        """Helper method to retrieve combination info for a product."""
        with MockRequest(self.env, website=self.ar_website):
            return self.product_1._get_additionnal_combination_info(
                product_or_template=product_id or self.product_1,
                quantity=quantity,
                uom=self.uom_unit,
                date=datetime(2025, 5, 21),
                website=self.ar_website
            )

    def test_default_website_sale_legal_values(self):
        """Ensure legal default values are applied on AR website."""
        self.assertEqual(self.ar_website.l10n_ar_website_sale_show_both_prices, True)
        self.assertEqual(self.ar_website.show_line_subtotals_tax_selection, 'tax_included')

    def test_price_calculation_with_tax_changes(self):
        """Test list price and tax excluded price calculations for various tax setups."""
        with self.subTest(scenario="Single 21% VAT - tax excluded"):
            combo = self._get_combination_info()
            self.assertDictContains(combo, {
                'list_price': 1210.00,  # 1000 + 21%
                'l10n_ar_price_tax_excluded': 1000.00,
            })

        with self.cr.savepoint():
            with self.subTest(scenario="Mixed taxes - 10.5% excluded + 27% included"):
                template = self.env['account.chart.template']
                tax_27_included = template.ref('ri_tax_vat_27_ventas')
                tax_10_5_excluded = template.ref('ri_tax_vat_10_ventas')

                tax_27_included.price_include = True
                tax_10_5_excluded.price_include = False

                self.product_1.taxes_id = (tax_27_included + tax_10_5_excluded).ids
                combo = self._get_combination_info()
                self.assertDictContains(combo, {
                    'list_price': 1082.68,                 # Computed price including all taxes
                    'l10n_ar_price_tax_excluded': 787.40,  # Reverse calculated base price
                })

    def test_product_variant_prices_with_attributes(self):
        """Test variant-specific price calculation with color attribute values."""
        self.product_1.taxes_id = self.env['account.chart.template'].ref('ri_tax_vat_21_ventas')

        # Add attribute line and values to product template
        attribute_line = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.product_1.id,
            'attribute_id': self.color_attribute.id,
            'value_ids': [(6, 0, [self.color_white.id, self.color_black.id])]
        })

        # Set price extras for each variant
        attribute_line.product_template_value_ids[0].price_extra = 100  # White
        attribute_line.product_template_value_ids[1].price_extra = 200  # Black

        white_variant = self.product_1.product_variant_ids[0]
        black_variant = self.product_1.product_variant_ids[1]

        with self.subTest(scenario="White variant with 100 extra + 21% VAT"):
            combo = self._get_combination_info(product_id=white_variant)
            self.assertDictContains(combo, {
                'list_price': 1331.00,                # (1000+100) + 21%
                'l10n_ar_price_tax_excluded': 1100.00,
            })

        with self.subTest(scenario="Black variant with 200 extra + 21% VAT"):
            combo = self._get_combination_info(product_id=black_variant)
            self.assertDictContains(combo, {
                'list_price': 1452.00,                # (1000+200) + 21%
                'l10n_ar_price_tax_excluded': 1200.00,
            })
