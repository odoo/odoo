from odoo import Command, fields
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged


@tagged("post_install", "post_install_l10n", "-at_install")
class TestAustraliaTparReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="au"):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_a.vat = '22 225 459 588'
        cls.partner_b.vat = '11 225 459 588'

    def test_tpar(self):
        purch_tpar_tax = self.env.ref(f'account.{self.env.company.id}_au_tax_purchase_10_service_tpar')
        purch_tpar_no_abn_tax = self.env.ref(f'account.{self.env.company.id}_au_tax_purchase_10_service_tpar_no_abn')
        (purch_tpar_tax + purch_tpar_no_abn_tax).write({'active': True})

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
                        'tax_ids': [Command.set(purch_tpar_tax.ids)],
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
                        'tax_ids': [Command.set(purch_tpar_no_abn_tax.ids)],
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
