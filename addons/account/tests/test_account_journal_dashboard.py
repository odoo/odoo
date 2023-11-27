from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools.misc import format_amount

@tagged('post_install', '-at_install')
class TestAccountJournalDashboard(AccountTestInvoicingCommon):

    @freeze_time("2019-01-22")
    def test_customer_invoice_dashboard(self):
        journal = self.company_data['default_journal_sale']

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': journal.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-21',
            'date': '2019-01-21',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 40.0,
                'name': 'product test 1',
                'discount': 10.00,
                'price_unit': 2.27,
                'tax_ids': [],
            })]
        })
        refund = self.env['account.move'].create({
            'move_type': 'out_refund',
            'journal_id': journal.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-21',
            'date': '2019-01-21',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'name': 'product test 1',
                'price_unit': 13.3,
                'tax_ids': [],
            })]
        })

        # Check Draft
        dashboard_data = journal.get_journal_dashboard_datas()

        self.assertEqual(dashboard_data['number_draft'], 2)
        self.assertIn('68.42', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 0)
        self.assertIn('0.00', dashboard_data['sum_waiting'])

        # Check Both
        invoice.action_post()

        dashboard_data = journal.get_journal_dashboard_datas()
        self.assertEqual(dashboard_data['number_draft'], 1)
        self.assertIn('-\N{ZERO WIDTH NO-BREAK SPACE}13.30', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 1)
        self.assertIn('81.72', dashboard_data['sum_waiting'])

        # Check waiting payment
        refund.action_post()

        dashboard_data = journal.get_journal_dashboard_datas()
        self.assertEqual(dashboard_data['number_draft'], 0)
        self.assertIn('0.00', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 2)
        self.assertIn('68.42', dashboard_data['sum_waiting'])

        # Check partial
        payment = self.env['account.payment'].create({
            'amount': 10.0,
            'payment_type': 'outbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
        })
        payment.action_post()

        (refund + payment.move_id).line_ids\
            .filtered(lambda line: line.account_type == 'asset_receivable')\
            .reconcile()

        dashboard_data = journal.get_journal_dashboard_datas()
        self.assertEqual(dashboard_data['number_draft'], 0)
        self.assertIn('0.00', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 2)
        self.assertIn('78.42', dashboard_data['sum_waiting'])

        dashboard_data = journal.get_journal_dashboard_datas()
        self.assertEqual(dashboard_data['number_late'], 2)
        self.assertIn('78.42', dashboard_data['sum_late'])

    def test_sale_purchase_journal_for_multi_currency_purchase(self):
        currency = self.currency_data['currency']
        company_currency = self.company_data['currency']

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': currency.id,
            'invoice_line_ids': [
                (0, 0, {'name': 'test', 'price_unit': 200})
            ],
        })
        invoice.action_post()

        payment = self.env['account.payment'].create({
            'amount': 90.0,
            'date': '2016-01-01',
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.partner_a.id,
            'currency_id': currency.id,
        })
        payment.action_post()

        (invoice + payment.move_id).line_ids.filtered_domain([
            ('account_id', '=', self.company_data['default_account_payable'].id)
        ]).reconcile()

        dashboard_data = self.company_data['default_journal_purchase'].get_journal_dashboard_datas()
        self.assertEqual(format_amount(self.env, 70, company_currency), dashboard_data['sum_waiting'])
        self.assertEqual(format_amount(self.env, 70, company_currency), dashboard_data['sum_late'])

    def test_sale_purchase_journal_for_multi_currency_sale(self):
        currency = self.currency_data['currency']
        company_currency = self.company_data['currency']

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': currency.id,
            'invoice_line_ids': [
                (0, 0, {'name': 'test', 'price_unit': 200})
            ],
        })
        invoice.action_post()

        payment = self.env['account.payment'].create({
            'amount': 90.0,
            'date': '2016-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'currency_id': currency.id,
        })
        payment.action_post()

        (invoice + payment.move_id).line_ids.filtered_domain([
            ('account_id', '=', self.company_data['default_account_receivable'].id)
        ]).reconcile()

        dashboard_data = self.company_data['default_journal_sale'].get_journal_dashboard_datas()
        self.assertEqual(format_amount(self.env, 70, company_currency), dashboard_data['sum_waiting'])
        self.assertEqual(format_amount(self.env, 70, company_currency), dashboard_data['sum_late'])

    def test_gap_in_sequence_warning(self):
        journal = self.company_data['default_journal_sale']
        self.assertFalse(journal._query_has_sequence_holes())  # No moves so no gap
        moves = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'journal_id': journal.id,
            'partner_id': self.partner_a.id,
            'invoice_date': f'1900-01-{i+1:02d}',
            'date': f'2019-01-{i+1:02d}',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'quantity': 40.0,
                'name': 'product test 1',
                'price_unit': 2.27,
                'tax_ids': [],
            })]
        } for i in range(12)]).sorted('date')
        gap_date = moves[6].date

        moves.action_post()
        self.assertFalse(journal._query_has_sequence_holes())  # no gap, no gap warning

        moves[5:7].button_draft()
        self.assertFalse(journal._query_has_sequence_holes())  # no gap (with draft moves using sequence numbers), no gap warning
        moves[6].unlink()
        self.assertTrue(journal._query_has_sequence_holes())  # gap due to missing sequence, gap warning

        moves[5:6].action_post()
        self.company_data['company'].write({'fiscalyear_lock_date': gap_date + relativedelta(days=1)})
        self.assertFalse(journal._query_has_sequence_holes())  # gap but prior to lock-date, no gap warning

        moves[10].button_draft()
        moves[10].button_cancel()
        self.assertTrue(journal._query_has_sequence_holes())  # gap due to canceled move using a sequence, no gap warning
