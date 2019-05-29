from unittest.mock import patch

from odoo.addons.account.tests.account_test_users import AccountTestUsers
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountJournalDashboard(AccountTestUsers):
    def test_customer_invoice_dashboard(self):
        def patched_today(*args, **kwargs):
            return '2019-01-22'

        date_invoice = '2019-01-21'

        journal = self.env['account.journal'].create({
            'name': 'sale_0',
            'code': 'SALE0',
            'type': 'sale',
        })

        invoice = self.env['account.move'].create({
            'type': 'out_invoice',
            'journal_id': journal.id,
            'partner_id': self.env.ref('base.res_partner_3').id,
            'invoice_date': date_invoice,
            'date': date_invoice,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.env.ref('product.product_product_1').id,
                'quantity': 40.0,
                'name': 'product test 1',
                'discount': 10.00,
                'price_unit': 2.27,
            })]
        })
        refund = self.env['account.move'].create({
            'type': 'out_refund',
            'journal_id': journal.id,
            'partner_id': self.env.ref('base.res_partner_3').id,
            'invoice_date': '2019-01-21',
            'date': date_invoice,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.env.ref('product.product_product_1').id,
                'quantity': 1.0,
                'name': 'product test 1',
                'price_unit': 13.3,
            })]
        })

        # Check Draft
        dashboard_data = journal.get_journal_dashboard_datas()

        self.assertEquals(dashboard_data['number_draft'], 2)
        self.assertIn('68.42', dashboard_data['sum_draft'])

        self.assertEquals(dashboard_data['number_waiting'], 0)
        self.assertIn('0.00', dashboard_data['sum_waiting'])

        # Check Both
        invoice.post()

        dashboard_data = journal.get_journal_dashboard_datas()
        self.assertEquals(dashboard_data['number_draft'], 1)
        self.assertIn('-13.30', dashboard_data['sum_draft'])

        self.assertEquals(dashboard_data['number_waiting'], 1)
        self.assertIn('81.72', dashboard_data['sum_waiting'])

        # Check waiting payment
        refund.post()

        dashboard_data = journal.get_journal_dashboard_datas()
        self.assertEquals(dashboard_data['number_draft'], 0)
        self.assertIn('0.00', dashboard_data['sum_draft'])

        self.assertEquals(dashboard_data['number_waiting'], 2)
        self.assertIn('68.42', dashboard_data['sum_waiting'])

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
        self.env['account.move.line'].with_context(check_move_validity=False).create({
            'move_id': payment_move.id,
            'account_id': self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_liquidity').id)], limit=1).id,
            'credit': 10.00,
        })

        payment_move.post()

        refund.js_assign_outstanding_line(payment_move_line.id)

        dashboard_data = journal.get_journal_dashboard_datas()
        self.assertEquals(dashboard_data['number_draft'], 0)
        self.assertIn('0.00', dashboard_data['sum_draft'])

        self.assertEquals(dashboard_data['number_waiting'], 2)
        self.assertIn('78.42', dashboard_data['sum_waiting'])

        with patch('odoo.fields.Date.today', patched_today):
            dashboard_data = journal.get_journal_dashboard_datas()
            self.assertEquals(dashboard_data['number_late'], 2)
            self.assertIn('78.42', dashboard_data['sum_late'])
