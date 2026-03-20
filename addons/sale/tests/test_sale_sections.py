from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleSections(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tax_1 = cls.env['account.tax'].create({
            'name': 'Tax 1',
            'amount': 10,
        })
        cls.tax_2 = cls.env['account.tax'].create({
            'name': 'Tax 2',
            'amount': 20,
        })
        cls.sections_sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [
                Command.create({
                    'name': 'r1',
                    'product_id': cls.product.id,
                    'price_unit': 10,
                }),
                Command.create({
                    'name': 'Sec1',
                    'display_type': 'line_section',
                }),
                Command.create({
                    'name': 'Sec1-r1',
                    'product_id': cls.product.id,
                    'tax_ids': cls.tax_2.ids,
                    'price_unit': 200,
                }),
                Command.create({
                    'name': 'Sec1-Sub1',
                    'display_type': 'line_subsection',
                    'collapse_composition': True,
                }),
                Command.create({
                    'name': 'Sec1-Sub1-r1',
                    'product_id': cls.product.id,
                    'tax_ids': (cls.tax_1 + cls.tax_2).ids,
                    'price_unit': 300,
                }),
                Command.create({
                    'name': 'Sec1-Sub1-r2',
                    'product_id': cls.product.id,
                    'tax_ids': (cls.tax_1 + cls.tax_2).ids,
                    'price_unit': 300,
                }),
                Command.create({
                    'name': 'Sec1-Sub1-r3',
                    'product_id': cls.product.id,
                    'tax_ids': cls.tax_1.ids,
                    'price_unit': 100,
                }),
                Command.create({
                    'name': 'Sec1-Sub2',
                    'display_type': 'line_subsection',
                    'collapse_composition': True,
                }),
                Command.create({
                    'name': 'Sec1-Sub2-r1',
                    'product_id': cls.product.id,
                    'tax_ids': cls.tax_2.ids,
                    'price_unit': 200,
                }),
                Command.create({
                    'name': 'Sec1-Sub2-r2',
                    'product_id': cls.product.id,
                    'tax_ids': cls.tax_1.ids,
                    'price_unit': 100,
                }),
            ],
        })

    def test_sale_order_line_parent_id(self):
        """Verify correct assignment of `parent_id`:

        - Lines with no preceding section/subsection → no parent.
        - Section's children (lines + subsections) → parent is the section.
        - Subsection's children → parent is the subsection.
        """
        self.assertFalse(self.sections_sale_order.order_line[0].parent_id)
        self.assertEqual(
            self.sections_sale_order.order_line[2].parent_id,
            self.sections_sale_order.order_line[1],
        )
        self.assertEqual(
            self.sections_sale_order.order_line[3].parent_id,
            self.sections_sale_order.order_line[1],
        )
        self.assertEqual(
            self.sections_sale_order.order_line[4].parent_id,
            self.sections_sale_order.order_line[3],
        )

    def test_sale_order_report_line_visibility_and_grouping(self):
        """Check report utils for sections.

        - `_get_order_lines_to_report` must exclude children of collapsed sections/subsections,
        but keep regular lines and headers in order.
        - `_get_grouped_section_summary` must correctly aggregate totals by tax.
        """
        lines_to_report = self.sections_sale_order._get_order_lines_to_report()
        self.assertEqual(len(lines_to_report), 5)
        self.assertEqual(
            lines_to_report.mapped('name'),
            ['r1', 'Sec1', 'Sec1-r1', 'Sec1-Sub1', 'Sec1-Sub2'],
            "Lines of hidden subsection shouldn't be visible in report",
        )

        subsection_summary_lines = lines_to_report[3]._get_grouped_section_summary()
        self.assertEqual(len(subsection_summary_lines), 2)

        self.assertEqual(subsection_summary_lines[0]['price_subtotal'], 600.00)
        self.assertEqual(subsection_summary_lines[1]['price_subtotal'], 100.00)

    def test_sale_order_sections_totals(self):
        """Ensure section totals are computed correctly.

        A `line_section` should aggregate the subtotals of all following product
        order lines that belong to it, including those under nested subsections.
        Aggregation must stop when another section or subsection is encountered.
        """
        self.assertEqual(
            self.sections_sale_order.order_line[1]._get_section_totals('price_subtotal'),
            sum(self.sections_sale_order.order_line[1:].mapped('price_subtotal')),
        )
        self.assertEqual(
            self.sections_sale_order.order_line[3]._get_section_totals('price_subtotal'),
            sum(self.sections_sale_order.order_line[4:7].mapped('price_subtotal')),
        )
        self.assertEqual(
            self.sections_sale_order.order_line[7]._get_section_totals('price_subtotal'),
            sum(self.sections_sale_order.order_line[8:].mapped('price_subtotal')),
        )
