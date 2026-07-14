# tests/test_baiwang_discounts.py

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestBaiwangDiscounts(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.cn').id,
            'vat': '91310000TEST12345X',
        })
        cls.tax_category = cls.env['l10n_cn_edi.tax.category'].sudo().create({'name': 'Test Category',
            'code': '1090618030000000000',
        })

    def test_proportional_global_discount(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'price_unit': 600.0,
                    'quantity': 1.0,
                    'l10n_cn_tax_category_id': self.tax_category.id,
                }),
                (0, 0, {
                    'product_id': self.product_b.id,
                    'price_unit': 900.0,
                    'quantity': 2.0,
                    'l10n_cn_tax_category_id': self.tax_category.id,
                }),
                (0, 0, {
                    'name': 'Global Discount',
                    'price_unit': -240.0,
                    'quantity': 1.0,
                }),
            ],
        })
        payload_lines = invoice._l10n_cn_baiwang_prepare_lines()
        self.assertEqual(len(payload_lines), 4)
        self.assertEqual(payload_lines[0]['invoiceLineNature'], '2')
        self.assertEqual(payload_lines[1]['invoiceLineNature'], '1')
        self.assertEqual(payload_lines[2]['invoiceLineNature'], '2')
        self.assertEqual(payload_lines[3]['invoiceLineNature'], '1')
        self.assertAlmostEqual(payload_lines[1]['goodsTotalPrice'], -60.0, places=2)
        self.assertAlmostEqual(payload_lines[3]['goodsTotalPrice'], -180.0, places=2)
