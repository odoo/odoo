from odoo import Command, fields
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged


@tagged("post_install", "post_install_l10n", "-at_install")
class TestAustraliaTparReport(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('au')
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_a.vat = '22 225 459 588'
        cls.partner_b.vat = '11 225 459 588'

        cls.purch_tpar_tax = cls.env.ref(f'account.{cls.env.company.id}_au_tax_purchase_10_service_tpar')
        cls.purch_tpar_no_abn_tax = cls.env.ref(f'account.{cls.env.company.id}_au_tax_purchase_10_service_tpar_no_abn')
        (cls.purch_tpar_tax + cls.purch_tpar_no_abn_tax).write({'active': True})

    def test_tpar(self):

        date_invoice = '2023-01-01'
        bills = self.env['account.move'].create([
            {
                'move_type': 'in_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': date_invoice,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'line_1',
                        'quantity': 1.0,
                        'price_unit': 500.0,
                        'tax_ids': [Command.set(self.purch_tpar_tax.ids)],
                    }),
                ],
            },
            {
                'move_type': 'in_invoice',
                'partner_id': self.partner_b.id,
                'invoice_date': date_invoice,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'line_1',
                        'quantity': 1.0,
                        'price_unit': 300.0,
                        'tax_ids': [Command.set(self.purch_tpar_no_abn_tax.ids)],
                    }),
                ],
            }
        ])

        bills.action_post()

        for bill in bills:
            self.env['account.payment.register'].with_context(active_model='account.move', active_ids=bill.ids).create({
                'payment_date': date_invoice,
                'journal_id': self.company_data['default_journal_bank'].id,
                'amount': bill.amount_total,
            })._create_payments()

            self.assertEqual(bill.payment_state, 'in_payment')

        # Customer payments shouldn't affect the report
        self.env['account.payment'].create({
            'amount': 1000.0,
            'payment_type': 'inbound',
            'partner_id': self.partner_a.id,
            'date': date_invoice,
        }).action_post()

        tpar_report = self.env.ref('l10n_au_reports.tpar_report')

        options = self._generate_options(tpar_report, fields.Date.from_string('2023-01-01'), fields.Date.from_string('2023-12-31'))
        options['unfold_all'] = True

        self.assertLinesValues(
            # pylint: disable=C0326
            tpar_report._get_lines(options),
            #    Name,                       ABN, Total GST, Gross Paid, Tax Withheld
            [    0,                            1,         2,          3,           4,],
            [
                ('partner_a',   "22 225 459 588",       50.0,       550.0,       0.0,),
                ('partner_b',   "11 225 459 588",       30.0,       189.0,     141.0,),
                ('Total',                     "",       80.0,       739.0,     141.0,),
            ],
            options,
        )

    def test_bank_statement_only_tpar_widget(self):
        today = fields.Date.context_today(self.env.user)
        date_from = today.replace(month=1, day=1)
        date_to = today.replace(month=12, day=31)

        # Create vendor bill
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': today,
            'company_id': self.env.company.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'TPAR service',
                    'price_unit': 400.0,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.purch_tpar_tax.ids)],
                }),
            ],
        })
        bill.action_post()

        st_line = self.env['account.bank.statement.line'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'partner_id': self.partner_a.id,
            'amount': -bill.amount_total,
            'payment_ref': f'Payment {bill.name}',
        })

        # Get payable line from invoice
        payable_line = bill.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable')
        self.assertTrue(payable_line)

        # Reconcile via bank rec widget (THIS IS THE KEY)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})

        wizard._action_add_new_amls(payable_line)
        wizard._action_validate()

        # Sanity check: invoice is paid
        self.assertTrue(payable_line.reconciled)

        # Run TPAR report
        tpar_report = self.env.ref('l10n_au_reports.tpar_report')
        options = self._generate_options(tpar_report, date_from, date_to)

        # Bank statement line should be included
        self.assertTrue(self.env['l10n_au.report.handler']._execute_query(options, raise_warning=True))

        self.assertLinesValues(
            # pylint: disable=C0326
            tpar_report._get_lines(options),
            #    Name,                       ABN, Total GST, Gross Paid, Tax Withheld
            [    0,                            1,         2,          3,           4],
            [
                ('partner_a',   "22 225 459 588",       40.0,       440.0,       0.0),
                ('Total',                     "",       40.0,       440.0,        ''),
            ],
            options,
        )
