from datetime import date
from odoo import Command
from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestLibroGiornaleReport(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('it')
    def setUpClass(cls):
        super().setUpClass()

        cls.company.write({
            'vat': 'IT12345670017',
        })

        cls.partner = cls.env['res.partner'].create({
            'name': 'Libro Giornale Partner',
            'country_id': cls.env.ref('base.it').id,
            'vat': 'IT00313371213',
        })

        cls.report = cls.env.ref('l10n_it_reports.account_financial_report_libro_giornale')
        cls.handler = cls.env['l10n_it.libro_giornale.report.handler']

    def _create_move(self, date, debit=1000.0, credit=1000.0, account_name='Test Account'):
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'partner_id': self.partner.id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'date': date,
            'line_ids':[
                Command.create({
                    'account_id': self.company_data['default_account_receivable'].id,
                    'name': 'Debit line',
                    'debit': debit,
                    'credit': 0.0,
                }),
                Command.create({
                    'account_id': self.company_data['default_account_payable'].id,
                    'name': 'Credit line',
                    'debit': 0.0,
                    'credit': credit,
                })
            ],
        })
        move.action_post()
        return move

    def _get_libro_giornale_lines(self, date_from, date_to):
        options = self._generate_options(
            self.report,
            date_from,
            date_to,
        )
        data = self.handler._generate_document_data_for_export(self.report, options, export_type='pdf')
        return data['journals_vals'][0]['lines']

    def test_export_contains_expected_fields(self):
        # Create test journal entries
        move1 = self._create_move('2024-01-01', debit=1000.0, credit=1000.0)
        move2 = self._create_move('2024-01-02', debit=2000.0, credit=2000.0)

        # Generate report data
        options = self._generate_options(self.report, '2024-01-01', '2024-01-31')
        data = self.handler._generate_document_data_for_export(self.report, options, export_type='pdf')
        lines = data['journals_vals'][0]['lines']

        # Skip the total row
        data_lines = lines[:-1]

        # Expected values
        expected_values = [
            {
                'journal_entry': move1.name,
                'date': date(2024, 1, 1),
                'debit': '1,000.00\xa0€',
                'credit': '0.00\xa0€',
            },
            {
                'journal_entry': move1.name,
                'date': date(2024, 1, 1),
                'debit': '0.00\xa0€',
                'credit': '1,000.00\xa0€',
            },
            {
                'journal_entry': move2.name,
                'date': date(2024, 1, 2),
                'debit': '2,000.00\xa0€',
                'credit': '0.00\xa0€',
            },
            {
                'journal_entry': move2.name,
                'date': date(2024, 1, 2),
                'debit': '0.00\xa0€',
                'credit': '2,000.00\xa0€',
            }
        ]

        for i, line in enumerate(data_lines):
            result = {
                'journal_entry': line['journal_entry']['data'],
                'date': line['date']['data'],
                'debit': line['debit']['data'],
                'credit': line['credit']['data'],
            }

            self.assertDictEqual(
                result,
                expected_values[i],
                f"Mismatch in line {i}"
            )

    def test_total_row_values_are_correct(self):
        # Create test journal entries
        self._create_move('2024-01-01', debit=500.0, credit=500.0)
        self._create_move('2024-01-02', debit=1500.0, credit=1500.0)

        # Get report lines
        lines = self._get_libro_giornale_lines('2024-01-01', '2024-01-31')
        total_row = lines[-1]

        # Compute expected totals
        expected_total_debit = '2,000.00\xa0€'
        expected_total_credit = '2,000.00\xa0€'

        # Assertions
        self.assertEqual(total_row.get('name', {}).get('data'), 'Total', "Total row should be labeled 'Total'")
        self.assertIn('debit', total_row, "Total row missing 'debit' field")
        self.assertIn('credit', total_row, "Total row missing 'credit' field")

        self.assertEqual(total_row['debit']['data'], expected_total_debit, "Incorrect total debit value")
        self.assertEqual(total_row['credit']['data'], expected_total_credit, "Incorrect total credit value")

    def test_line_numbering_is_sequential(self):
        for i in range(3):
            self._create_move(f'2024-01-0{i+1}')
        lines = self._get_libro_giornale_lines('2024-01-01', '2024-01-31')

        numbers = [line['line_number']['data'] for line in lines if 'line_number' in line]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)), "Line numbers are not sequential.")

    def test_total_row_exists(self):
        self._create_move('2024-01-05', debit=500, credit=500)
        lines = self._get_libro_giornale_lines('2024-01-01', '2024-01-31')
        total_row = lines[-1]

        self.assertEqual(total_row.get('name', {}).get('data'), 'Total', "Last row should be a total row.")
        self.assertIn('credit', total_row, "Total row missing 'credit' column.")
        self.assertIn('debit', total_row, "Total row missing 'debit' column.")

    def test_debit_credit_totals_are_correct(self):
        self._create_move('2024-01-05', debit=200, credit=200)
        self._create_move('2024-01-06', debit=300, credit=300)
        lines = self._get_libro_giornale_lines('2024-01-01', '2024-01-31')

        total_debit = sum(line.get('debit_float', 0.0) for line in lines)
        total_credit = sum(line.get('credit_float', 0.0) for line in lines)

        total_row = lines[-1]
        reported_debit = float(total_row['debit']['data'][:-1])
        reported_credit = float(total_row['credit']['data'][:-1])

        self.assertAlmostEqual(reported_debit, total_debit, msg="Total debit mismatch")
        self.assertAlmostEqual(reported_credit, total_credit, msg="Total credit mismatch")

    def test_lines_without_account_name_have_no_line_number(self):
        self._create_move('2024-01-10')
        lines = self._get_libro_giornale_lines('2024-01-01', '2024-01-31')

        for line in lines:
            if not line.get('account_name'):
                self.assertNotIn('line_number', line, "Line without account_name should not have line_number")

    def test_open_report_libro_giornale(self):
        self._create_move('2024-01-05', debit=200, credit=200)
        self._create_move('2024-01-06', debit=300, credit=300)
        options = self._generate_options(self.report, '2024-01-01', '2024-01-31', {'unfold_all': True})
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                             1,              2,          3],
            [
                ("Libro Giornale"                          "",             "",         ""),
                ("Miscellaneous Operations",           "MISC",          500.0,      500.0),
                ("150100 Customer receivables",      "150100",          500.0,        0.0),
                ("250100 Accounts payable",          "250100",            0.0,      500.0),
            ],
            options,
        )

    def test_libro_giornale_with_bank_journal(self):
        self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2024-01-07',
            'line_ids': [
                Command.create({'debit': 100.0, 'credit': 0.0, 'account_id': self.company_data['default_journal_bank'].default_account_id.id}),
                Command.create({'debit': 0.0, 'credit': 100.0, 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        }).action_post()
        # Get report data
        lines = self._get_libro_giornale_lines('2024-01-01', '2024-01-31')
        # Assert the final row is the total row
        total_row = lines[-1]
        self.assertEqual(total_row['debit']['data'], total_row['credit']['data'])
