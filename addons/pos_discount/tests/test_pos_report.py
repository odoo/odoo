# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_pos_report import TestPosReportCommon


@tagged('post_install', '-at_install')
class TestPosDiscountReport(TestPosReportCommon):

    def test_tax_totals_exclude_global_discount(self):
        discount_product = self.create_product(
            'Report Global Discount', self.categ_basic, 0, tax_ids=self.tax.ids,
        )
        self.basic_config.write({
            'module_pos_discount': True,
            'discount_product_id': discount_product.id,
        })
        self._create_report_order([
            (self.coffee, 1, 100, 0),
            (discount_product, 1, -10, 0),
        ])

        sections = self._report_sections(session_id=self.session.id)
        totals = next(section['values'] for section in sections if section['section_id'] == 'taxes_sales')
        lines = self._unfold('taxes_sales')

        self.assertEqual(totals, {'base_amount': 430, 'tax_amount': 38, 'amount_total': 468})
        for key, total in totals.items():
            self.assertEqual(total, sum(line['values'][key] for line in lines))
