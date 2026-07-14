from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestBaiwangDiscounts(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].country_id = cls.env.ref('base.cn')
        cls.tax_category = cls.env['l10n_cn_edi.tax.category'].sudo().create({
            'name': 'Test Category',
            'code': '1090618030000000000',
        })

    def test_proportional_global_discount(self):
        """Test that a single negative line is split proportionally across positive lines."""
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                # Positive Line 1: $600
                (0, 0, {
                    'product_id': self.product_a.id,
                    'price_unit': 600.0,
                    'quantity': 1.0,
                    'l10n_cn_tax_category_id': self.tax_category.id,
                }),
                # Positive Line 2: $1800
                (0, 0, {
                    'product_id': self.product_b.id,
                    'price_unit': 900.0,
                    'quantity': 2.0,
                    'l10n_cn_tax_category_id': self.tax_category.id,
                }),
                # Negative Line: -$240 Global Discount
                (0, 0, {
                    'name': 'Global Discount',
                    'price_unit': -240.0,
                    'quantity': 1.0,
                }),
            ],
        })
        payload_lines = invoice._l10n_cn_baiwang_prepare_lines()
        self.assertEqual(len(payload_lines), 4)
        self.assertEqual(payload_lines[0]['invoiceLineNature'], '2')  # Discounted
        self.assertEqual(payload_lines[1]['invoiceLineNature'], '1')  # Discount
        self.assertEqual(payload_lines[2]['invoiceLineNature'], '2')  # Discounted
        self.assertEqual(payload_lines[3]['invoiceLineNature'], '1')  # Discount
        self.assertAlmostEqual(payload_lines[1]['goodsTotalPrice'], -60.0, places=2)
        self.assertAlmostEqual(payload_lines[3]['goodsTotalPrice'], -180.0, places=2)
