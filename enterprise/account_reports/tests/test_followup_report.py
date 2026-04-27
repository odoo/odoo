from .common import TestAccountReportsCommon

from odoo import Command, fields
from freezegun import freeze_time
from odoo.tools import format_date
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestFollowupReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.report = cls.env.ref('account_reports.followup_report')
        # Initiate Invoices
        with freeze_time('2025-10-08'):
            cls.today = fields.Date.today()
        invoices_data = [
            # Partner A invoices
            {'partner': cls.partner_a, 'amount': 100.0, 'due_date': '2025-01-01'},
            {'partner': cls.partner_a, 'amount': 100.0, 'due_date': cls.today},
            {'partner': cls.partner_a, 'amount': 100.0, 'due_date': '2025-01-01', 'move_type': 'out_refund'},
            # Partner B invoices
            {'partner': cls.partner_b, 'amount': 100.0, 'due_date': '2025-01-01'},
            {'partner': cls.partner_b, 'amount': 100.0, 'due_date': cls.today},
            {'partner': cls.partner_b, 'amount': 400.0, 'due_date': '2025-01-01', 'move_type': 'out_refund'},
        ]
        for invoice_data in invoices_data:
            cls.init_invoice(
                move_type=invoice_data.get('move_type', 'out_invoice'),
                partner=invoice_data['partner'],
                amounts=[invoice_data['amount']],
                invoice_date_due=invoice_data['due_date'],
                invoice_date=invoice_data.get('invoice_date', '2025-01-01'),
            )
        cls.formatted_today = format_date(cls.env, cls.today, date_format='MM/dd/YYY')

    @classmethod
    def init_invoice(cls, move_type, partner=None, invoice_date=None, post=False, products=None, amounts=None, taxes=None, company=False, currency=None, journal=None, invoice_date_due=None):
        move = super().init_invoice(move_type, partner, invoice_date, False, products, amounts, taxes, company, currency, journal)
        if invoice_date_due:
            move.invoice_payment_term_id = False
            move.invoice_date_due = invoice_date_due
        move.action_post()
        return move

    @freeze_time('2025-10-08')
    def test_followup_report_unfold(self):
        ''' Test unfolding a line when rendering the whole report, having overdue and due sections '''
        options = self._generate_options(self.report, fields.Date.from_string('2025-01-01'), fields.Date.from_string('2025-01-31'))
        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                  Amount          Balance
            [   0,                                      3,              5],
            [
                ('partner_a',                       100.0,          100.0),
                ('partner_b',                      -200.0,         -200.0),
                ('Total',                          -100.0,         -100.0),
            ],
            options
        )

        options['unfolded_lines'] = [self.report._get_generic_line_id('res.partner', self.partner_a.id)]
        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Due Date        Amount        Balance
            [   0,                                            2,            3,              5],
            [
                ('partner_a',                                '',        100.0,          100.0),
                ('Overdue',                                  '',           '',             ''),
                ('INV/2025/00001',                 '01/01/2025',        100.0,          100.0),
                ('RINV/2025/00001',                '01/01/2025',       -100.0,            0.0),
                ('Due',                                      '',           '',             ''),
                ('INV/2025/00002',         self.formatted_today,        100.0,          100.0),
                ('Total partner_a',                          '',        100.0,          100.0),
                ('partner_b',                                '',       -200.0,         -200.0),
                ('Total',                                    '',       -100.0,         -100.0),
            ],
            options
        )

    @freeze_time('2025-10-08')
    def test_followup_report_load_more(self):
        ''' Test loading more lines when reaching the limit '''
        self.report.load_more_limit = 2

        invoices_data = [
            {'amount': 100.0, 'due_date': '2024-12-03'},
            {'amount': 100.0, 'due_date': self.today}
        ]

        for invoice_data in invoices_data:
            self.init_invoice(
                move_type='out_invoice',
                partner=self.partner_a,
                amounts=[invoice_data['amount']],
                invoice_date_due=invoice_data['due_date'],
                invoice_date='2025-01-01',
            )

        options = self._generate_options(self.report, fields.Date.from_string('2025-01-01'), fields.Date.from_string('2025-01-31'))
        options['unfolded_lines'] = [self.report._get_generic_line_id('res.partner', self.partner_a.id)]

        report_lines = self.report._get_lines(options)

        self.assertLinesValues(
            report_lines,
            #   Name                                    Due Date        Amount       Balance
            [   0,                                            2,            3,             5],
            [
                ('partner_a',                                '',        300.0,         300.0),
                ('Overdue',                                  '',           '',            ''),
                ('INV/2025/00005',                 '12/03/2024',        100.0,         100.0),
                ('INV/2025/00001',                 '01/01/2025',        100.0,         200.0),
                ('Load more...',                             '',           '',            ''),
                ('Total partner_a',                          '',        300.0,         300.0),
                ('partner_b',                                '',       -200.0,        -200.0),
                ('Total',                                    '',        100.0,         100.0),
            ],
            options
        )

        options['unfolded_lines'] = [line['id'] for line in report_lines if line.get('unfolded')]

        load_more_1 = self.report.get_expanded_lines(
            options,
            report_lines[0]['id'],
            report_lines[4]['groupby'],
            '_report_expand_unfoldable_line_partner_ledger',
            report_lines[4]['progress'],
            report_lines[4]['offset'],
            None,
        )

        self.assertLinesValues(
            load_more_1,
            #   Name                                    Due Date        Amount          Balance
            [   0,                                            2,            3,             5],
            [
                ('RINV/2025/00001',                '01/01/2025',       -100.0,         100.0),
                ('Due',                                      '',           '',            ''),
                ('INV/2025/00002',         self.formatted_today,        100.0,         200.0),
                ('Load more...',                             '',           '',            ''),
            ],
            options
        )

        options['unfolded_lines'] = options['unfolded_lines'] + [line['id'] for line in load_more_1 if line.get('unfolded')]

        load_more_2 = self.report.get_expanded_lines(
            options,
            report_lines[0]['id'],
            load_more_1[3]['groupby'],
            '_report_expand_unfoldable_line_partner_ledger',
            load_more_1[3]['progress'],
            load_more_1[3]['offset'],
            None,
        )

        self.assertLinesValues(
            load_more_2,
            #   Name                                    Due Date        Amount          Balance
            [   0,                                            2,            3,             5],
            [
                ('INV/2025/00006',         self.formatted_today,        100.0,          300.0),
            ],
            options
        )
