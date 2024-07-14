# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.tests.common import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tools.misc import NON_BREAKING_SPACE


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCustomerStatements(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        # Create an invoice prior to the report period to have a starting balance.
        cls.init_invoice("out_invoice", cls.partner_a, "2022-12-31", amounts=[750], post=True)
        # Create an invoice in the report period.
        cls.first_move = cls.init_invoice("out_invoice", cls.partner_a, "2023-01-01", amounts=[1000, 2000], post=True)
        # Create an invoice in the report period and pay it.
        cls.paid_move = cls.init_invoice("out_invoice", cls.partner_a, "2023-01-10", amounts=[3000], post=True)
        cls.payment = cls.env['account.payment.register'].create({
            'payment_date': cls.paid_move.date,
            'line_ids': cls.paid_move.line_ids.filtered(lambda l: l.display_type == 'payment_term'),
        })._create_payments()

    def test_statement_from_report(self):
        # Get the report
        options = {
            'date': {'date_from': '2023-01-01', 'date_to': '2023-01-31'},
            'report_id': self.env.ref('account_reports.partner_ledger_report').id,
        }
        action = self.partner_a.action_print_customer_statements(options)
        data = action['context']['report_action']['data']

        # 1. Ensure consistency of the lines
        self.assertDictEqual(
            data['lines'],
            {
                self.partner_a.id: [
                    {
                        'date': '1 Jan 23',
                        'activity': 'Initial Balance',
                        'reference': '',
                        'due_date': '',
                        'amount': '',
                        'move_type': '',
                        'balance': f'${NON_BREAKING_SPACE}750.00',
                    }, {
                        'date': '1 Jan 23',
                        'activity': self.first_move.name,
                        'reference': None,
                        'due_date': '1 Jan 23',
                        'amount': f'${NON_BREAKING_SPACE}3,000.00',
                        'move_type': 'Invoice',
                        'balance': f'${NON_BREAKING_SPACE}3,750.00',
                    }, {
                        'date': '10 Jan 23',
                        'activity': self.paid_move.name,
                        'reference': None,
                        'due_date': '10 Jan 23',
                        'amount': f'${NON_BREAKING_SPACE}3,000.00',
                        'move_type': 'Invoice',
                        'balance': f'${NON_BREAKING_SPACE}6,750.00',
                    }, {
                        'date': '10 Jan 23',
                        'activity': self.payment.name,
                        'reference': self.paid_move.name,
                        'due_date': '',
                        'amount': f'${NON_BREAKING_SPACE}-3,000.00',
                        'move_type': '⬅Payment',
                        'balance': f'${NON_BREAKING_SPACE}3,750.00',
                    }
                ]
            })
        # 2. Validate the balances due
        self.assertDictEqual(
            data['balances_due'],
            {self.partner_a.id: f'${NON_BREAKING_SPACE}3,750.00'}
        )

    def test_statement_from_report_unreconciled_only(self):
        # Get the report
        options = {
            'date': {'date_from': '2023-01-01', 'date_to': '2023-01-31'},
            'report_id': self.env.ref('account_reports.partner_ledger_report').id,
            'unreconciled': True,
        }
        action = self.partner_a.action_print_customer_statements(options)
        data = action['context']['report_action']['data']

        # 1. Ensure consistency of the lines
        self.assertDictEqual(
            data['lines'],
            {
                self.partner_a.id: [
                    {
                        'date': '1 Jan 23',
                        'activity': 'Initial Balance',
                        'reference': '',
                        'due_date': '',
                        'amount': '',
                        'move_type': '',
                        'balance': f'${NON_BREAKING_SPACE}750.00',
                    }, {
                        'date': '1 Jan 23',
                        'activity': self.first_move.name,
                        'reference': None,
                        'due_date': '1 Jan 23',
                        'amount': f'${NON_BREAKING_SPACE}3,000.00',
                        'move_type': 'Invoice',
                        'balance': f'${NON_BREAKING_SPACE}3,750.00',
                    }
                ]
            })
        # 2. Validate the balances due
        self.assertDictEqual(
            data['balances_due'],
            {self.partner_a.id: f'${NON_BREAKING_SPACE}3,750.00'}
        )

    @freeze_time('2023-01-25')  # When printing from a customer directly, we print for the current month.
    def test_statement_from_customer(self):
        # Mostly the same, besides that we don't have any options.
        action = self.partner_a.action_print_customer_statements()
        data = action['context']['report_action']['data']

        # 1. Ensure consistency of the lines
        self.assertDictEqual(
            data['lines'],
            {
                self.partner_a.id: [
                    {
                        'date': '1 Jan 23',
                        'activity': 'Initial Balance',
                        'reference': '',
                        'due_date': '',
                        'amount': '',
                        'move_type': '',
                        'balance': f'${NON_BREAKING_SPACE}750.00',
                    }, {
                        'date': '1 Jan 23',
                        'activity': self.first_move.name,
                        'reference': None,
                        'due_date': '1 Jan 23',
                        'amount': f'${NON_BREAKING_SPACE}3,000.00',
                        'move_type': 'Invoice',
                        'balance': f'${NON_BREAKING_SPACE}3,750.00',
                    }, {
                        'date': '10 Jan 23',
                        'activity': self.paid_move.name,
                        'reference': None,
                        'due_date': '10 Jan 23',
                        'amount': f'${NON_BREAKING_SPACE}3,000.00',
                        'move_type': 'Invoice',
                        'balance': f'${NON_BREAKING_SPACE}6,750.00',
                    }, {
                        'date': '10 Jan 23',
                        'activity': self.payment.name,
                        'reference': self.paid_move.name,
                        'due_date': '',
                        'amount': f'${NON_BREAKING_SPACE}-3,000.00',
                        'move_type': '⬅Payment',
                        'balance': f'${NON_BREAKING_SPACE}3,750.00',
                    }
                ]
            })
        # 2. Validate the balances due
        self.assertDictEqual(
            data['balances_due'],
            {self.partner_a.id: f'${NON_BREAKING_SPACE}3,750.00'}
        )
