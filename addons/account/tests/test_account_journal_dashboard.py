from unittest.mock import patch

from odoo.addons.account.tests.common import AccountTestUsersCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountJournalDashboard(AccountTestUsersCommon):
    def test_customer_invoice_dashboard(self):
        def patched_today(*args, **kwargs):
            return '2019-01-22'

        date_invoice = '2019-01-21'

        journal = self.env['account.journal'].create({
            'name': 'sale_0',
            'code': 'SALE0',
            'type': 'sale',
        })

        res_partner_3 = self.env['res.partner'].create({
            'name': 'Gemini Furniture',
        })

        product_product_1 = self.env['product.product'].create({
            'name': 'Virtual Interior Design',
            'standard_price': 20.5,
            'list_price': 30.75,
            'type': 'service',
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': journal.id,
            'partner_id': res_partner_3.id,
            'invoice_date': date_invoice,
            'date': date_invoice,
            'invoice_line_ids': [(0, 0, {
                'product_id': product_product_1.id,
                'quantity': 40.0,
                'name': 'product test 1',
                'discount': 10.00,
                'price_unit': 2.27,
            })]
        })
        refund = self.env['account.move'].create({
            'move_type': 'out_refund',
            'journal_id': journal.id,
            'partner_id': res_partner_3.id,
            'invoice_date': '2019-01-21',
            'date': date_invoice,
            'invoice_line_ids': [(0, 0, {
                'product_id': product_product_1.id,
                'quantity': 1.0,
                'name': 'product test 1',
                'price_unit': 13.3,
            })]
        })

        currency = self.env.company.currency_id

        # Check Draft
        dashboard_data = journal.get_journal_dashboard_datas()

        self.assertEqual(dashboard_data['number_draft'], 2)
        # expected_amount = 68.42, but because of rounding in amount_total, it can become 69
        expected_amount = currency.round(invoice.amount_total - refund.amount_total)
        # avoid using formatLang to keep the test as simple as possible and improve coverage
        expected_amount_str = "%.{0}f".format(currency.decimal_places) % expected_amount
        self.assertIn(expected_amount_str, dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 0)
        expected_amount = 0.0
        expected_amount_str = "%.{0}f".format(currency.decimal_places) % expected_amount
        self.assertIn(expected_amount_str, dashboard_data['sum_waiting'])

        # Check Both
        invoice.post()

        dashboard_data = journal.get_journal_dashboard_datas()
        self.assertEqual(dashboard_data['number_draft'], 1)
        expected_amount = -13.3
        expected_amount_str = "%.{0}f".format(currency.decimal_places) % expected_amount
        self.assertIn(expected_amount_str, dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 1)
        # expected_amount = 81.72, but because of rounding in amount_total, it can become 82
        expected_amount = currency.round(invoice.amount_total)
        expected_amount_str = "%.{0}f".format(currency.decimal_places) % expected_amount
        self.assertIn(expected_amount_str, dashboard_data['sum_waiting'])

        # Check waiting payment
        refund.post()

        dashboard_data = journal.get_journal_dashboard_datas()
        self.assertEqual(dashboard_data['number_draft'], 0)
        expected_amount = 0.0
        expected_amount_str = "%.{0}f".format(currency.decimal_places) % expected_amount
        self.assertIn(expected_amount_str, dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 2)
        # expected_amount = 68.42, but because of rounding in amount_total, it can become 69
        expected_amount = currency.round(invoice.amount_total - refund.amount_total)
        expected_amount_str = "%.{0}f".format(currency.decimal_places) % expected_amount
        self.assertIn(expected_amount_str, dashboard_data['sum_waiting'])

        # Check partial
        receivable_account = refund.line_ids.mapped('account_id').filtered(lambda a: a.internal_type == 'receivable')
        payment_move = self.env['account.move'].create({
            'journal_id': journal.id,
        })
        payment_move_line = self.env['account.move.line'].with_context(check_move_validity=False).create({
            'move_id': payment_move.id,
            'account_id': receivable_account.id,
            'debit': 10.00,
        })
        domain = [('user_type_id', '=', self.env.ref('account.data_account_type_liquidity').id), ('company_id', '=', payment_move.company_id.id)]
        self.env['account.move.line'].with_context(check_move_validity=False).create({
            'move_id': payment_move.id,
            'account_id': self.env['account.account'].search(domain, limit=1).id,
            'credit': 10.00,
        })

        payment_move.post()

        refund.js_assign_outstanding_line(payment_move_line.id)

        dashboard_data = journal.get_journal_dashboard_datas()
        self.assertEqual(dashboard_data['number_draft'], 0)
        expected_amount = 0.0
        expected_amount_str = "%.{0}f".format(currency.decimal_places) % expected_amount
        self.assertIn(expected_amount_str, dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 2)
        # expected_amount = 78.42, but because of rounding in amount_total, it can become 79
        expected_amount = currency.round(invoice.amount_total - refund.amount_total + payment_move.amount_total)
        expected_amount_str = "%.{0}f".format(currency.decimal_places) % expected_amount
        self.assertIn(expected_amount_str, dashboard_data['sum_waiting'])

        with patch('odoo.fields.Date.today', patched_today):
            dashboard_data = journal.get_journal_dashboard_datas()
            self.assertEqual(dashboard_data['number_late'], 2)
            # expected_amount = 78.42, but because of rounding in amount_total, it can become 79
            expected_amount = currency.round(invoice.amount_total - refund.amount_total + payment_move.amount_total)
            expected_amount_str = "%.{0}f".format(currency.decimal_places) % expected_amount
            self.assertIn(expected_amount_str, dashboard_data['sum_late'])
