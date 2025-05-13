# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountReport(AccountTestInvoicingCommon):

    def test_copy_report(self):
        """ Ensure that copying a report correctly adjust codes, formulas and subformulas. """
        report = self.env['account.report'].create({
            'name': "Report To Copy",
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance'})],
            'line_ids': [
                Command.create({
                    'name': "test_line_1",
                    'code': "test_line_1",
                    'sequence': 1,
                    'expression_ids': [
                        Command.create({
                            'date_scope': 'strict_range',
                            'engine': 'external',
                            'formula': 'sum',
                            'label': 'balance',
                        }),
                    ]
                }),
                Command.create({
                    'name': "test_line_2",
                    'code': "test_line_2",
                    'sequence': 2,
                    'expression_ids': [
                        Command.create({
                            'date_scope': 'strict_range',
                            'engine': 'aggregation',
                            'formula': 'test_line_1',
                            'subformula': 'if_other_expr_above(test_line_1.balance, USD(0))',
                            'label': 'balance',
                        })
                    ],
                })
            ]
        })
        copy = report.copy()
        # Ensure that the two line codes are updated.
        self.assertEqual(copy.line_ids[0].code, 'test_line_1_COPY')
        self.assertEqual(copy.line_ids[1].code, 'test_line_2_COPY')
        # Ensure that the line 2 expression formula and subformula point to the correct code.
        expression = copy.line_ids[1].expression_ids
        self.assertEqual(expression.formula, 'test_line_1_COPY')
        self.assertEqual(expression.subformula, 'if_other_expr_above(test_line_1_COPY.balance, USD(0))')
