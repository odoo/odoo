from odoo.addons.account.tests.account_test_classes import AccountingTestCase

from odoo.tools import pycompat


class TestReconciliation(AccountingTestCase):

    def setUp(self):
        super(TestReconciliation, self).setUp()
        self.account_reconciliation_model = self.env['account.reconciliation']
        self.so_model = self.env['sale.order']

    def test_reconcile_reconciliation(self):
        partner = self.env.ref("base.res_partner_2")
        product = self.env.ref('product.product_order_01')
        statement = self.env.ref('account.demo_bank_statement_1')
        statement_line = self.env.ref('account.demo_bank_statement_line_1')
        so = self.env.ref('sale.sale_order_19')

        data = self.account_reconciliation_model.get_data_for_reconciliation_widget(statement_line.ids)
        data[0]['st_line'].pop('date')
        data[0]['st_line'].pop('id')

        account = self.env['account.account'].search([('code', '=', '101401'), ('name', '=', 'Bank')])
        journal = self.env['account.journal'].search([('code', '=', 'BNK1')])

        self.assertDictEqual(data[0], {
            'st_line': {
                'currency_id': 3,
                'communication_partner_name': False,
                'open_balance_account_id': statement_line.partner_id.property_account_receivable_id.id,
                'name': u'SAJ/2014/002 and SAJ/2014/003',
                'partner_name': u'Agrolait',
                'partner_id': partner.id,
                'has_no_partner': False,
                'journal_id': journal.id,
                'account_id': [account.id, u'101401 Bank'],
                'account_name': u'Bank',
                'note': '',
                'amount': 1175.0,
                'amount_str': u'$ 1,175.00',
                'amount_currency_str': '',
                'account_code': u'101401',
                'ref': u'',
                'statement_id': statement.id
            },
            'order_ids': so.ids,
            'reconciliation_proposition': []
        })