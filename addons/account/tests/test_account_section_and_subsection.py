from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountSectionAndSubsection(AccountTestInvoicingCommon):

    def test_get_child_lines_with_one_taxes(self):
        move = self.init_invoice('out_invoice')
        move.invoice_line_ids = [
            Command.create({
                'name': "Section 1",
                'display_type': 'line_section',
                'collapse_prices': True,
            }),
            Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100,
                'tax_ids': self.tax_sale_a.ids,
            }),
            Command.create({
                'name': "Subsection 1.1",
                'display_type': 'line_subsection',
                'collapse_composition': True,
            }),
            Command.create({
                'product_id': self.product_a.id,
                'price_unit': 200,
                'tax_ids': self.tax_sale_a.ids,
            }),
            Command.create({
                'product_id': self.product_b.id,
                'price_unit': 100,
                'tax_ids': self.tax_sale_a.ids,
            }),
        ]
        section_lines = move.invoice_line_ids[0]._get_child_lines()
        expected_values = [
            {'display_type': 'line_section', 'name': 'Section 1', 'price_subtotal': 400.0, 'taxes': ['15%']},
            {'display_type': 'product', 'name': 'product_a', 'price_subtotal': 100.0, 'taxes': []},
            {'display_type': 'product', 'name': 'Subsection 1.1', 'price_subtotal': 300.0, 'taxes': []},
        ]
        for expected_value, line_value in zip(expected_values, section_lines):
            for key, value in expected_value.items():
                self.assertEqual(line_value[key], value)

    def test_get_child_lines_with_multiple_taxes(self):
        move = self.init_invoice('out_invoice')
        move.invoice_line_ids = [
            Command.create({
                'name': "Section 1",
                'display_type': 'line_section',
                'collapse_prices': True,
            }),
            Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100,
                'tax_ids': self.tax_sale_a.ids,
            }),
            Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100,
                'tax_ids': self.tax_sale_b.ids,
            }),
            Command.create({
                'name': "Subsection 1.1",
                'display_type': 'line_subsection',
                'collapse_composition': True,
            }),
            Command.create({
                'product_id': self.product_b.id,
                'price_unit': 200,
                'tax_ids': self.tax_sale_a.ids,
            }),
            Command.create({
                'product_id': self.product_b.id,
                'price_unit': 200,
                'tax_ids': self.tax_sale_b.ids,
            }),
        ]
        section_lines = move.invoice_line_ids[0]._get_child_lines()
        expected_values = [
            {'display_type': 'line_section', 'name': 'Section 1', 'price_subtotal': 300.0, 'taxes': ['15%']},
            {'display_type': 'product', 'name': 'product_a', 'price_subtotal': 100.0, 'taxes': []},
            {'display_type': 'product', 'name': 'Subsection 1.1', 'price_subtotal': 200.0, 'taxes': []},
            {'display_type': 'line_section', 'name': 'Section 1', 'price_subtotal': 300.0, 'taxes': ['15% (copy)']},
            {'display_type': 'product', 'name': 'product_a', 'price_subtotal': 100.0, 'taxes': []},
            {'display_type': 'product', 'name': 'Subsection 1.1', 'price_subtotal': 200.0, 'taxes': []},
        ]
        for expected_value, line_value in zip(expected_values, section_lines):
            for key, value in expected_value.items():
                self.assertEqual(line_value[key], value)
