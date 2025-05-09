from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountReport(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a test report with lines and expressions to test copy functionality
        cls.test_report = cls.env['account.report'].create({
            'name': 'Test Report',
            'sequence': 1,
        })

        # Create parent line with code and expression
        cls.parent_line = cls.env['account.report.line'].create({
            'name': 'Parent Line',
            'code': 'PARENT',
            'report_id': cls.test_report.id,
            'expression_ids': [Command.create({
                'label': 'balance',
                'engine': 'aggregation',
                'formula': 'CHILD1.balance + CHILD2.balance',
            })],
            'children_ids': [
                Command.create({
                    'name': 'Child Line 1',
                    'code': 'CHILD1',
                    'report_id': cls.test_report.id,
                }),
                Command.create({
                    'name': 'Child Line 2',
                    'code': 'CHILD2',
                    'report_id': cls.test_report.id,
                })
            ]
        })

    def test_report_line_copy_and_uniqueness(self):
        """Test the copy functionality of report lines including naming, code generation, formula updates and uniqueness"""
        # Test first copy
        first_copy = self.parent_line.copy()

        # Test copied name and code generation
        self.assertEqual(first_copy.name, "Parent Line (copy)")
        self.assertEqual(first_copy.code, "PARENT_COPY")

        # Test children were copied
        self.assertEqual(len(first_copy.children_ids), 2)

        # Test child lines have appropriate codes and names
        copied_children_codes = first_copy.children_ids.mapped('code')
        self.assertIn('CHILD1_COPY', copied_children_codes)
        self.assertIn('CHILD2_COPY', copied_children_codes)

        # Test expression was copied and formula was updated
        copied_expression = first_copy.expression_ids.filtered(lambda e: e.engine == 'aggregation')
        self.assertEqual(copied_expression.formula, 'CHILD1_COPY.balance + CHILD2_COPY.balance')

        # Test second copy for name and code uniqueness
        second_copy = self.parent_line.copy()
        self.assertEqual(second_copy.name, "Parent Line (copy) (copy)")
        self.assertEqual(second_copy.code, "PARENT_COPY_COPY")
