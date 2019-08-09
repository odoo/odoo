from odoo import api, fields
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged
import time
import unittest


# TODO in master
# The name of this class should be TestReconciliationHelpers
class TestReconciliation(AccountingTestCase):

    """Tests for reconciliation (account.tax)

    Test used to check that when doing a sale or purchase invoice in a different currency,
    the result will be balanced.
    """

    def setUp(self):
        super(TestReconciliation, self).setUp()
        self.account_invoice_model = self.env['account.invoice']
        self.account_invoice_line_model = self.env['account.invoice.line']
        self.acc_bank_stmt_model = self.env['account.bank.statement']
        self.acc_bank_stmt_line_model = self.env['account.bank.statement.line']
        self.res_currency_model = self.registry('res.currency')
        self.res_currency_rate_model = self.registry('res.currency.rate')

        partner_agrolait = self.env.ref("base.res_partner_2")
        self.partner_agrolait_id = partner_agrolait.id
        self.currency_swiss_id = self.env.ref("base.CHF").id
        self.currency_usd_id = self.env.ref("base.USD").id
        self.currency_euro_id = self.env.ref("base.EUR").id
        company = self.env.ref('base.main_company')
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", [self.currency_euro_id, company.id])
        self.account_rcv = partner_agrolait.property_account_receivable_id or self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_receivable').id)], limit=1)
        self.account_rsa = partner_agrolait.property_account_payable_id or self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_payable').id)], limit=1)
        self.product = self.env.ref("product.product_product_4")

        self.bank_journal_euro = self.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'BNK67'})
        self.account_euro = self.bank_journal_euro.default_debit_account_id

        self.bank_journal_usd = self.env['account.journal'].create({'name': 'Bank US', 'type': 'bank', 'code': 'BNK68', 'currency_id': self.currency_usd_id})
        self.account_usd = self.bank_journal_usd.default_debit_account_id

        self.fx_journal = self.env['res.users'].browse(self.env.uid).company_id.currency_exchange_journal_id
        self.diff_income_account = self.env['res.users'].browse(self.env.uid).company_id.income_currency_exchange_account_id
        self.diff_expense_account = self.env['res.users'].browse(self.env.uid).company_id.expense_currency_exchange_account_id

        self.inbound_payment_method = self.env['account.payment.method'].create({
            'name': 'inbound',
            'code': 'IN',
            'payment_type': 'inbound',
        })

        self.expense_account = self.env['account.account'].create({
            'name': 'EXP',
            'code': 'EXP',
            'user_type_id': self.env.ref('account.data_account_type_expenses').id,
            'company_id': company.id,
        })
        # cash basis intermediary account
        self.tax_waiting_account = self.env['account.account'].create({
            'name': 'TAX_WAIT',
            'code': 'TWAIT',
            'user_type_id': self.env.ref('account.data_account_type_current_liabilities').id,
            'reconcile': True,
            'company_id': company.id,
        })
        # cash basis final account
        self.tax_final_account = self.env['account.account'].create({
            'name': 'TAX_TO_DEDUCT',
            'code': 'TDEDUCT',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
            'company_id': company.id,
        })
        self.tax_base_amount_account = self.env['account.account'].create({
            'name': 'TAX_BASE',
            'code': 'TBASE',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
            'company_id': company.id,
        })

        # Journals
        self.purchase_journal = self.env['account.journal'].create({
            'name': 'purchase',
            'code': 'PURCH',
            'type': 'purchase',
        })
        self.cash_basis_journal = self.env['account.journal'].create({
            'name': 'CABA',
            'code': 'CABA',
            'type': 'general',
        })
        self.general_journal = self.env['account.journal'].create({
            'name': 'general',
            'code': 'GENE',
            'type': 'general',
        })

        # Tax Cash Basis
        self.tax_cash_basis = self.env['account.tax'].create({
            'name': 'cash basis 20%',
            'type_tax_use': 'purchase',
            'company_id': company.id,
            'amount': 20,
            'account_id': self.tax_waiting_account.id,
            'tax_exigibility': 'on_payment',
            'cash_basis_account_id': self.tax_final_account.id,
            'cash_basis_base_account_id': self.tax_base_amount_account.id,
        })

    def create_invoice(self, type='out_invoice', invoice_amount=50, currency_id=None):
        #we create an invoice in given currency
        invoice = self.account_invoice_model.create({'partner_id': self.partner_agrolait_id,
            'currency_id': currency_id,
            'name': type == 'out_invoice' and 'invoice to client' or 'invoice to vendor',
            'account_id': self.account_rcv.id,
            'type': type,
            'date_invoice': time.strftime('%Y') + '-07-01',
            })
        self.account_invoice_line_model.create({'product_id': self.product.id,
            'quantity': 1,
            'price_unit': invoice_amount,
            'invoice_id': invoice.id,
            'name': 'product that cost ' + str(invoice_amount),
            'account_id': self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1).id,
        })

        #validate invoice
        invoice.action_invoice_open()
        return invoice

    def make_payment(self, invoice_record, bank_journal, amount=0.0, amount_currency=0.0, currency_id=None):
        bank_stmt = self.acc_bank_stmt_model.create({
            'journal_id': bank_journal.id,
            'date': time.strftime('%Y') + '-07-15',
            'name': 'payment' + invoice_record.number
        })

        bank_stmt_line = self.acc_bank_stmt_line_model.create({'name': 'payment',
            'statement_id': bank_stmt.id,
            'partner_id': self.partner_agrolait_id,
            'amount': amount,
            'amount_currency': amount_currency,
            'currency_id': currency_id,
            'date': time.strftime('%Y') + '-07-15',})

        #reconcile the payment with the invoice
        for l in invoice_record.move_id.line_ids:
            if l.account_id.id == self.account_rcv.id:
                line_id = l
                break
        amount_in_widget = currency_id and amount_currency or amount
        bank_stmt_line.process_reconciliation(counterpart_aml_dicts=[{
            'move_line': line_id,
            'debit': amount_in_widget < 0 and -amount_in_widget or 0.0,
            'credit': amount_in_widget > 0 and amount_in_widget or 0.0,
            'name': line_id.name,
            }])
        return bank_stmt

    def make_customer_and_supplier_flows(self, invoice_currency_id, invoice_amount, bank_journal, amount, amount_currency, transaction_currency_id):
        #we create an invoice in given invoice_currency
        invoice_record = self.create_invoice(type='out_invoice', invoice_amount=invoice_amount, currency_id=invoice_currency_id)
        #we encode a payment on it, on the given bank_journal with amount, amount_currency and transaction_currency given
        bank_stmt = self.make_payment(invoice_record, bank_journal, amount=amount, amount_currency=amount_currency, currency_id=transaction_currency_id)
        customer_move_lines = bank_stmt.move_line_ids

        #we create a supplier bill in given invoice_currency
        invoice_record = self.create_invoice(type='in_invoice', invoice_amount=invoice_amount, currency_id=invoice_currency_id)
        #we encode a payment on it, on the given bank_journal with amount, amount_currency and transaction_currency given
        bank_stmt = self.make_payment(invoice_record, bank_journal, amount=-amount, amount_currency=-amount_currency, currency_id=transaction_currency_id)
        supplier_move_lines = bank_stmt.move_line_ids
        return customer_move_lines, supplier_move_lines


@tagged('post_install', '-at_install')
class TestReconciliationExec(TestReconciliation):

    def test_statement_usd_invoice_eur_transaction_eur(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_euro_id, 30, self.bank_journal_usd, 42, 30, self.currency_euro_id)
        self.assertRecordValues(customer_move_lines, [
            {'debit': 30.0,     'credit': 0.0,      'amount_currency': 42,  'currency_id': self.currency_usd_id},
            {'debit': 0.0,      'credit': 30.0,     'amount_currency': -42, 'currency_id': self.currency_usd_id},
        ])
        self.assertRecordValues(supplier_move_lines, [
            {'debit': 0.0,      'credit': 30.0,     'amount_currency': -42, 'currency_id': self.currency_usd_id},
            {'debit': 30.0,     'credit': 0.0,      'amount_currency': 42,  'currency_id': self.currency_usd_id},
        ])

    def test_statement_usd_invoice_usd_transaction_usd(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_usd, 50, 0, False)
        self.assertRecordValues(customer_move_lines, [
            {'debit': 32.70,    'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_usd_id},
            {'debit': 0.0,      'credit': 32.70,    'amount_currency': -50, 'currency_id': self.currency_usd_id},
        ])
        self.assertRecordValues(supplier_move_lines, [
            {'debit': 0.0,      'credit': 32.70,    'amount_currency': -50, 'currency_id': self.currency_usd_id},
            {'debit': 32.70,    'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_usd_id},
        ])

    def test_statement_usd_invoice_usd_transaction_eur(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_usd, 50, 40, self.currency_euro_id)
        self.assertRecordValues(customer_move_lines, [
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_usd_id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -50, 'currency_id': self.currency_usd_id},
        ])
        exchange_lines = customer_move_lines.mapped('full_reconcile_id.exchange_move_id.line_ids')
        self.assertRecordValues(exchange_lines, [
             {'debit': 0.0,     'credit': 7.30,     'account_id': self.diff_income_account.id},
             {'debit': 7.30,    'credit': 0.0,      'account_id': self.account_rcv.id},
        ])

        self.assertRecordValues(supplier_move_lines, [
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -50, 'currency_id': self.currency_usd_id},
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_usd_id},
        ])
        exchange_lines = supplier_move_lines.mapped('full_reconcile_id.exchange_move_id.line_ids')
        self.assertRecordValues(exchange_lines, [
             {'debit': 7.30,    'credit': 0.0,      'account_id': self.diff_expense_account.id},
             {'debit': 0.0,     'credit': 7.30,     'account_id': self.account_rcv.id},
        ])

    def test_statement_usd_invoice_chf_transaction_chf(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_swiss_id, 50, self.bank_journal_usd, 42, 50, self.currency_swiss_id)
        self.assertRecordValues(customer_move_lines, [
            {'debit': 27.47,    'credit': 0.0,      'amount_currency': 42,  'currency_id': self.currency_usd_id},
            {'debit': 0.0,      'credit': 27.47,    'amount_currency': -50, 'currency_id': self.currency_swiss_id},
        ])
        exchange_lines = customer_move_lines.mapped('full_reconcile_id.exchange_move_id.line_ids')
        self.assertRecordValues(exchange_lines, [
            {'debit': 10.74,    'credit': 0.0,      'account_id': self.diff_expense_account.id},
            {'debit': 0.0,      'credit': 10.74,    'account_id': self.account_rcv.id},
        ])
        
        self.assertRecordValues(supplier_move_lines, [
            {'debit': 0.0,      'credit': 27.47,    'amount_currency': -42, 'currency_id': self.currency_usd_id},
            {'debit': 27.47,    'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_swiss_id},
        ])
        exchange_lines = supplier_move_lines.mapped('full_reconcile_id.exchange_move_id.line_ids')
        self.assertRecordValues(exchange_lines, [
            {'debit': 0.0,      'credit': 10.74,    'account_id': self.diff_income_account.id},
            {'debit': 10.74,    'credit': 0.0,      'account_id': self.account_rcv.id},
        ])

    def test_statement_eur_invoice_usd_transaction_usd(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_euro, 40, 50, self.currency_usd_id)
        self.assertRecordValues(customer_move_lines, [
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_usd_id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -50, 'currency_id': self.currency_usd_id},
        ])
        exchange_lines = customer_move_lines.mapped('full_reconcile_id.exchange_move_id.line_ids')
        self.assertRecordValues(exchange_lines, [
            {'debit': 0.0,      'credit': 7.30,     'account_id': self.diff_income_account.id},
            {'debit': 7.30,     'credit': 0.0,      'account_id': self.account_rcv.id},
        ])
        
        self.assertRecordValues(supplier_move_lines, [
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -50, 'currency_id': self.currency_usd_id},
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_usd_id},
        ])
        exchange_lines = supplier_move_lines.mapped('full_reconcile_id.exchange_move_id.line_ids')
        self.assertRecordValues(exchange_lines, [
            {'debit': 7.30,     'credit': 0.0,      'account_id': self.diff_expense_account.id},
            {'debit': 0.0,      'credit': 7.30,     'account_id': self.account_rcv.id},
        ])

    def test_statement_eur_invoice_usd_transaction_eur(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_euro, 40, 0.0, False)
        self.assertRecordValues(customer_move_lines, [
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 0.0, 'currency_id': False},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': 0.0, 'currency_id': False},
        ])
        self.assertRecordValues(supplier_move_lines, [
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': 0.0, 'currency_id': False},
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 0.0, 'currency_id': False},
        ])

    def test_statement_euro_invoice_usd_transaction_chf(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_euro, 42, 50, self.currency_swiss_id)
        self.assertRecordValues(customer_move_lines, [
            {'debit': 42.0,     'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_swiss_id},
            {'debit': 0.0,      'credit': 42.0,     'amount_currency': -50, 'currency_id': self.currency_swiss_id},
        ])
        self.assertRecordValues(supplier_move_lines, [
            {'debit': 0.0,      'credit': 42.0,     'amount_currency': -50, 'currency_id': self.currency_swiss_id},
            {'debit': 42.0,     'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_swiss_id},
        ])

    def test_statement_euro_invoice_usd_transaction_euro_full(self):
        #we create an invoice in given invoice_currency
        invoice_record = self.create_invoice(type='out_invoice', invoice_amount=50, currency_id=self.currency_usd_id)
        #we encode a payment on it, on the given bank_journal with amount, amount_currency and transaction_currency given
        bank_stmt = self.acc_bank_stmt_model.create({
            'journal_id': self.bank_journal_euro.id,
            'date': time.strftime('%Y') + '-01-01',
        })

        bank_stmt_line = self.acc_bank_stmt_line_model.create({'name': 'payment',
            'statement_id': bank_stmt.id,
            'partner_id': self.partner_agrolait_id,
            'amount': 40,
            'date': time.strftime('%Y') + '-01-01',})

        #reconcile the payment with the invoice
        for l in invoice_record.move_id.line_ids:
            if l.account_id.id == self.account_rcv.id:
                line_id = l
                break
        bank_stmt_line.process_reconciliation(counterpart_aml_dicts=[{
              'move_line': line_id,
              'debit': 0.0,
              'credit': 32.7,
              'name': 'test_statement_euro_invoice_usd_transaction_euro_full',
            }], new_aml_dicts=[{
              'debit': 0.0,
              'credit': 7.3,
              'name': 'exchange difference',
              'account_id': self.diff_income_account.id
            }])

        self.assertRecordValues(bank_stmt.move_line_ids, [
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 0.0,     'currency_id': False},
            {'debit': 0.0,      'credit': 32.7,     'amount_currency': 0.0,     'currency_id': False},
            {'debit': 0.0,      'credit': 7.3,      'amount_currency': 0.0,     'currency_id': False},
        ])

        # The invoice should be paid, as the payments totally cover its total
        self.assertEquals(invoice_record.state, 'paid', 'The invoice should be paid by now')
        invoice_rec_line = invoice_record.move_id.line_ids.filtered(lambda x: x.account_id.reconcile)
        self.assertTrue(invoice_rec_line.reconciled, 'The invoice should be totally reconciled')
        self.assertTrue(invoice_rec_line.full_reconcile_id, 'The invoice should have a full reconcile number')
        self.assertEquals(invoice_rec_line.amount_residual, 0, 'The invoice should be totally reconciled')
        self.assertEquals(invoice_rec_line.amount_residual_currency, 0, 'The invoice should be totally reconciled')

    @unittest.skip('adapt to new accounting')
    def test_balanced_exchanges_gain_loss(self):
        # The point of this test is to show that we handle correctly the gain/loss exchanges during reconciliations in foreign currencies.
        # For instance, with a company set in EUR, and a USD rate set to 0.033,
        # the reconciliation of an invoice of 2.00 USD (60.61 EUR) and a bank statement of two lines of 1.00 USD (30.30 EUR)
        # will lead to an exchange loss, that should be handled correctly within the journal items.
        env = api.Environment(self.cr, self.uid, {})
        # We update the currency rate of the currency USD in order to force the gain/loss exchanges in next steps
        rateUSDbis = env.ref("base.rateUSDbis")
        rateUSDbis.write({
            'name': time.strftime('%Y-%m-%d') + ' 00:00:00',
            'rate': 0.033,
        })
        # We create a customer invoice of 2.00 USD
        invoice = self.account_invoice_model.create({
            'partner_id': self.partner_agrolait_id,
            'currency_id': self.currency_usd_id,
            'name': 'Foreign invoice with exchange gain',
            'account_id': self.account_rcv_id,
            'type': 'out_invoice',
            'date_invoice': time.strftime('%Y-%m-%d'),
            'journal_id': self.bank_journal_usd_id,
            'invoice_line': [
                (0, 0, {
                    'name': 'line that will lead to an exchange gain',
                    'quantity': 1,
                    'price_unit': 2,
                })
            ]
        })
        invoice.action_invoice_open()
        # We create a bank statement with two lines of 1.00 USD each.
        statement = self.acc_bank_stmt_model.create({
            'journal_id': self.bank_journal_usd_id,
            'date': time.strftime('%Y-%m-%d'),
            'line_ids': [
                (0, 0, {
                    'name': 'half payment',
                    'partner_id': self.partner_agrolait_id,
                    'amount': 1.0,
                    'date': time.strftime('%Y-%m-%d')
                }),
                (0, 0, {
                    'name': 'second half payment',
                    'partner_id': self.partner_agrolait_id,
                    'amount': 1.0,
                    'date': time.strftime('%Y-%m-%d')
                })
            ]
        })

        # We process the reconciliation of the invoice line with the two bank statement lines
        line_id = None
        for l in invoice.move_id.line_id:
            if l.account_id.id == self.account_rcv_id:
                line_id = l
                break
        for statement_line in statement.line_ids:
            statement_line.process_reconciliation([
                {'counterpart_move_line_id': line_id.id, 'credit': 1.0, 'debit': 0.0, 'name': line_id.name}
            ])

        # The invoice should be paid, as the payments totally cover its total
        self.assertEquals(invoice.state, 'paid', 'The invoice should be paid by now')
        reconcile = None
        for payment in invoice.payment_ids:
            reconcile = payment.reconcile_id
            break
        # The invoice should be reconciled (entirely, not a partial reconciliation)
        self.assertTrue(reconcile, 'The invoice should be totally reconciled')
        result = {}
        exchange_loss_line = None
        for line in reconcile.line_id:
            res_account = result.setdefault(line.account_id, {'debit': 0.0, 'credit': 0.0, 'count': 0})
            res_account['debit'] = res_account['debit'] + line.debit
            res_account['credit'] = res_account['credit'] + line.credit
            res_account['count'] += 1
            if line.credit == 0.01:
                exchange_loss_line = line
        # We should be able to find a move line of 0.01 EUR on the Debtors account, being the cent we lost during the currency exchange
        self.assertTrue(exchange_loss_line, 'There should be one move line of 0.01 EUR in credit')
        # The journal items of the reconciliation should have their debit and credit total equal
        # Besides, the total debit and total credit should be 60.61 EUR (2.00 USD)
        self.assertEquals(sum(res['debit'] for res in result.values()), 60.61)
        self.assertEquals(sum(res['credit'] for res in result.items()), 60.61)
        counterpart_exchange_loss_line = None
        for line in exchange_loss_line.move_id.line_id:
            if line.account_id.id == self.account_fx_expense_id:
                counterpart_exchange_loss_line = line
        #  We should be able to find a move line of 0.01 EUR on the Foreign Exchange Loss account
        self.assertTrue(counterpart_exchange_loss_line, 'There should be one move line of 0.01 EUR on account "Foreign Exchange Loss"')

    def test_manual_reconcile_wizard_opw678153(self):

        def create_move(name, amount, amount_currency, currency_id):
            debit_line_vals = {
                'name': name,
                'debit': amount > 0 and amount or 0.0,
                'credit': amount < 0 and -amount or 0.0,
                'account_id': self.account_rcv.id,
                'amount_currency': amount_currency,
                'currency_id': currency_id,
            }
            credit_line_vals = debit_line_vals.copy()
            credit_line_vals['debit'] = debit_line_vals['credit']
            credit_line_vals['credit'] = debit_line_vals['debit']
            credit_line_vals['account_id'] = self.account_rsa.id
            credit_line_vals['amount_currency'] = -debit_line_vals['amount_currency']
            vals = {
                'journal_id': self.bank_journal_euro.id,
                'line_ids': [(0,0, debit_line_vals), (0, 0, credit_line_vals)]
            }
            return self.env['account.move'].create(vals).id
        move_list_vals = [
            ('1', -1.83, 0, self.currency_swiss_id),
            ('2', 728.35, 795.05, self.currency_swiss_id),
            ('3', -4.46, 0, self.currency_swiss_id),
            ('4', 0.32, 0, self.currency_swiss_id),
            ('5', 14.72, 16.20, self.currency_swiss_id),
            ('6', -737.10, -811.25, self.currency_swiss_id),
        ]
        move_ids = []
        for name, amount, amount_currency, currency_id in move_list_vals:
            move_ids.append(create_move(name, amount, amount_currency, currency_id))
        aml_recs = self.env['account.move.line'].search([('move_id', 'in', move_ids), ('account_id', '=', self.account_rcv.id), ('reconciled', '=', False)])
        aml_recs.reconcile()
        for aml in aml_recs:
            self.assertTrue(aml.reconciled, 'The journal item should be totally reconciled')
            self.assertEquals(aml.amount_residual, 0, 'The journal item should be totally reconciled')
            self.assertEquals(aml.amount_residual_currency, 0, 'The journal item should be totally reconciled')

        move_list_vals = [
            ('2', 728.35, 795.05, self.currency_swiss_id),
            ('3', -4.46, 0, False),
            ('4', 0.32, 0, False),
            ('5', 14.72, 16.20, self.currency_swiss_id),
            ('6', -737.10, -811.25, self.currency_swiss_id),
        ]
        move_ids = []
        for name, amount, amount_currency, currency_id in move_list_vals:
            move_ids.append(create_move(name, amount, amount_currency, currency_id))
        aml_recs = self.env['account.move.line'].search([('move_id', 'in', move_ids), ('account_id', '=', self.account_rcv.id), ('reconciled', '=', False)])
        aml_recs.reconcile(self.account_rsa, self.bank_journal_usd)
        for aml in aml_recs:
            self.assertTrue(aml.reconciled, 'The journal item should be totally reconciled')
            self.assertEquals(aml.amount_residual, 0, 'The journal item should be totally reconciled')
            self.assertEquals(aml.amount_residual_currency, 0, 'The journal item should be totally reconciled')

    def test_manual_reconcile_wizard_same_account(self):
        move_ids = self.env['account.move']
        debit_line_vals = {
                'name': '1',
                'debit': 728.35,
                'credit': 0.0,
                'account_id': self.account_rcv.id,
                'amount_currency': 795.05,
                'currency_id': self.currency_swiss_id,
            }
        credit_line_vals = {
                'name': '1',
                'debit': 0.0,
                'credit': 728.35,
                'account_id': self.account_rsa.id,
                'amount_currency': -795.05,
                'currency_id': self.currency_swiss_id,
            }
        vals = {
                'journal_id': self.bank_journal_euro.id,
                'date': time.strftime('%Y') + '-02-15',
                'line_ids': [(0,0, debit_line_vals), (0, 0, credit_line_vals)]
            }
        move_ids += self.env['account.move'].create(vals)
        debit_line_vals = {
                'name': '2',
                'debit': 0.0,
                'credit': 737.10,
                'account_id': self.account_rcv.id,
                'amount_currency': -811.25,
                'currency_id': self.currency_swiss_id,
            }
        credit_line_vals = {
                'name': '2',
                'debit': 737.10,
                'credit': 0.0,
                'account_id': self.account_rsa.id,
                'amount_currency': 811.25,
                'currency_id': self.currency_swiss_id,
            }
        vals = {
                'journal_id': self.bank_journal_euro.id,
                'date': time.strftime('%Y') + '-07-15',
                'line_ids': [(0,0, debit_line_vals), (0, 0, credit_line_vals)]
            }
        move_ids += self.env['account.move'].create(vals)

        account_move_line = move_ids.mapped('line_ids').filtered(lambda l: l.account_id == self.account_rcv)
        writeoff_vals = [{
                'account_id': self.account_rcv.id,
                'journal_id': self.bank_journal_euro.id,
                'date': time.strftime('%Y') + '-04-15',
                'debit': 8.75,
                'credit': 0.0
            }]
        writeoff_line = account_move_line._create_writeoff(writeoff_vals)
        (account_move_line + writeoff_line).reconcile()
        self.assertEquals(len(writeoff_line), 1, "The writeoff_line (balance_line) should have only one moves line")
        self.assertTrue(all(l.reconciled for l in writeoff_line), 'The balance lines should be totally reconciled')
        self.assertTrue(all(l.reconciled for l in account_move_line), 'The move lines should be totally reconciled')

    def test_reconcile_bank_statement_with_payment_and_writeoff(self):
        # Use case:
        # Company is in EUR, create a bill for 80 USD and register payment of 80 USD.
        # create a bank statement in USD bank journal with a bank statement line of 85 USD
        # Reconcile bank statement with payment and put the remaining 5 USD in bank fees or another account.

        invoice = self.create_invoice(type='out_invoice', invoice_amount=80, currency_id=self.currency_usd_id)
        # register payment on invoice
        payment = self.env['account.payment'].create({'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait_id,
            'amount': 80,
            'currency_id': self.currency_usd_id,
            'payment_date': time.strftime('%Y') + '-07-15',
            'journal_id': self.bank_journal_usd.id,
            })
        payment.post()
        payment_move_line = False
        bank_move_line = False
        for l in payment.move_line_ids:
            if l.account_id.id == self.account_rcv.id:
                payment_move_line = l
            else:
                bank_move_line = l
        invoice.register_payment(payment_move_line)

        # create bank statement
        bank_stmt = self.acc_bank_stmt_model.create({
            'journal_id': self.bank_journal_usd.id,
            'date': time.strftime('%Y') + '-07-15',
        })

        bank_stmt_line = self.acc_bank_stmt_line_model.create({'name': 'payment',
            'statement_id': bank_stmt.id,
            'partner_id': self.partner_agrolait_id,
            'amount': 85,
            'date': time.strftime('%Y') + '-07-15',})

        #reconcile the statement with invoice and put remaining in another account
        bank_stmt_line.process_reconciliation(payment_aml_rec= bank_move_line, new_aml_dicts=[{
            'account_id': self.diff_income_account.id,
            'debit': 0,
            'credit': 5,
            'name': 'bank fees',
            }])

        # Check that move lines associated to bank_statement are correct
        bank_stmt_aml = self.env['account.move.line'].search([('statement_id', '=', bank_stmt.id)])
        bank_stmt_aml |= bank_stmt_aml.mapped('move_id').mapped('line_ids')
        self.assertEquals(len(bank_stmt_aml), 4, "The bank statement should have 4 moves lines")
        lines = {
            self.account_usd.id: [
                {'debit': 3.27, 'credit': 0.0, 'amount_currency': 5, 'currency_id': self.currency_usd_id},
                {'debit': 52.33, 'credit': 0, 'amount_currency': 80, 'currency_id': self.currency_usd_id}
                ],
            self.diff_income_account.id: {'debit': 0.0, 'credit': 3.27, 'amount_currency': -5, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 0.0, 'credit': 52.33, 'amount_currency': -80, 'currency_id': self.currency_usd_id},
        }

        payments = bank_stmt_aml.mapped('payment_id')
        # creation and reconciliation of the over-amount statement
        # has created an another payment
        self.assertEqual(len(payments), 2)
        # Check amount of second, automatically created payment
        self.assertEqual((payments - payment).amount, 5)

        for aml in bank_stmt_aml:
            line = lines[aml.account_id.id]
            if type(line) == list:
                # find correct line inside the list
                if line[0]['debit'] == round(aml.debit, 2):
                    line = line[0]
                else:
                    line = line[1]
            self.assertEquals(round(aml.debit, 2), line['debit'])
            self.assertEquals(round(aml.credit, 2), line['credit'])
            self.assertEquals(round(aml.amount_currency, 2), line['amount_currency'])
            self.assertEquals(aml.currency_id.id, line['currency_id'])

    def test_partial_reconcile_currencies_01(self):
        #                client Account (payable, rsa)
        #        Debit                      Credit
        # --------------------------------------------------------
        # Pay a : 25/0.5 = 50       |   Inv a : 50/0.5 = 100
        # Pay b: 50/0.75 = 66.66    |   Inv b : 50/0.75 = 66.66
        # Pay c: 25/0.8 = 31.25     |
        #
        # Debit_currency = 100      | Credit currency = 100
        # Debit = 147.91            | Credit = 166.66
        # Balance Debit = 18.75
        # Counterpart Credit goes in Exchange diff

        dest_journal_id = self.env['account.journal'].search([('type', '=', 'purchase'), ('company_id', '=', self.env.ref('base.main_company').id)], limit=1)
        account_expenses = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_expenses').id)], limit=1)

        self.bank_journal_euro.write({'default_debit_account_id': self.account_rsa.id,
                                      'default_credit_account_id': self.account_rsa.id})
        dest_journal_id.write({'default_debit_account_id': self.account_rsa.id,
                               'default_credit_account_id': self.account_rsa.id})
        # Setting up rates for USD (main_company is in EUR)
        self.env['res.currency.rate'].create({'name': time.strftime('%Y') + '-' + '07' + '-01',
            'rate': 0.5,
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id})

        self.env['res.currency.rate'].create({'name': time.strftime('%Y') + '-' + '08' + '-01', 
            'rate': 0.75,
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id})

        self.env['res.currency.rate'].create({'name': time.strftime('%Y') + '-' + '09' + '-01', 
            'rate': 0.80,
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id})

        # Preparing Invoices (from vendor)
        invoice_a = self.account_invoice_model.create({'partner_id': self.partner_agrolait_id,
            'currency_id': self.currency_usd_id,
            'name': 'invoice to vendor',
            'account_id': self.account_rsa.id,
            'type': 'in_invoice',
            'date_invoice': time.strftime('%Y') + '-' + '07' + '-01',
            })
        self.account_invoice_line_model.create({'product_id': self.product.id,
            'quantity': 1,
            'price_unit': 50,
            'invoice_id': invoice_a.id,
            'name': 'product that cost ' + str(50),
            'account_id': account_expenses.id,
        })

        invoice_b = self.account_invoice_model.create({'partner_id': self.partner_agrolait_id,
            'currency_id': self.currency_usd_id,
            'name': 'invoice to vendor',
            'account_id': self.account_rsa.id,
            'type': 'in_invoice',
            'date_invoice': time.strftime('%Y') + '-' + '08' + '-01',
            })
        self.account_invoice_line_model.create({'product_id': self.product.id,
            'quantity': 1,
            'price_unit': 50,
            'invoice_id': invoice_b.id,
            'name': 'product that cost ' + str(50),
            'account_id': account_expenses.id,
        })

        invoice_a.action_invoice_open()
        invoice_b.action_invoice_open()

        # Preparing Payments
        # One partial for invoice_a (fully assigned to it)
        payment_a = self.env['account.payment'].create({'payment_type': 'outbound',
            'amount': 25,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_euro.id,
            'company_id': self.env.ref('base.main_company').id,
            'payment_date': time.strftime('%Y') + '-' + '07' + '-01',
            'partner_id': self.partner_agrolait_id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
            'destination_journal_id': dest_journal_id.id,
            'partner_type': 'supplier'})

        # One that will complete the payment of a, the rest goes to b
        payment_b = self.env['account.payment'].create({'payment_type': 'outbound',
            'amount': 50,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_euro.id,
            'company_id': self.env.ref('base.main_company').id,
            'payment_date': time.strftime('%Y') + '-' + '08' + '-01',
            'partner_id': self.partner_agrolait_id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
            'destination_journal_id': dest_journal_id.id,
            'partner_type': 'supplier'})

        # The last one will complete the payment of b
        payment_c = self.env['account.payment'].create({'payment_type': 'outbound',
            'amount': 25,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_euro.id,
            'company_id': self.env.ref('base.main_company').id,
            'payment_date': time.strftime('%Y') + '-' + '09' + '-01',
            'partner_id': self.partner_agrolait_id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
            'destination_journal_id': dest_journal_id.id,
            'partner_type': 'supplier'})

        payment_a.post()
        payment_b.post()
        payment_c.post()

        # Assigning payments to invoices
        debit_line_a = payment_a.move_line_ids.filtered(lambda l: l.debit and l.account_id == dest_journal_id.default_debit_account_id)
        debit_line_b = payment_b.move_line_ids.filtered(lambda l: l.debit and l.account_id == dest_journal_id.default_debit_account_id)
        debit_line_c = payment_c.move_line_ids.filtered(lambda l: l.debit and l.account_id == dest_journal_id.default_debit_account_id)

        invoice_a.assign_outstanding_credit(debit_line_a.id)
        invoice_a.assign_outstanding_credit(debit_line_b.id)
        invoice_b.assign_outstanding_credit(debit_line_b.id)
        invoice_b.assign_outstanding_credit(debit_line_c.id)

        # Asserting correctness (only in the payable account)
        full_reconcile = False
        for inv in (invoice_a + invoice_b):
            self.assertTrue(inv.reconciled)
            for aml in (inv.payment_move_line_ids + inv.move_id.line_ids).filtered(lambda l: l.account_id == self.account_rsa):
                self.assertEqual(aml.amount_residual, 0.0)
                self.assertEqual(aml.amount_residual_currency, 0.0)
                self.assertTrue(aml.reconciled)
                if not full_reconcile:
                    full_reconcile = aml.full_reconcile_id
                else:
                    self.assertTrue(aml.full_reconcile_id == full_reconcile)

        full_rec_move = full_reconcile.exchange_move_id
        # Globally check whether the amount is correct
        self.assertEqual(full_rec_move.amount, 18.75)

        # Checking if the direction of the move is correct
        full_rec_payable = full_rec_move.line_ids.filtered(lambda l: l.account_id == self.account_rsa)
        self.assertEqual(full_rec_payable.balance, 18.75)

    def test_unreconcile(self):
        # Use case:
        # 2 invoices paid with a single payment. Unreconcile the payment with one invoice, the
        # other invoice should remain reconciled.
        inv1 = self.create_invoice(invoice_amount=10, currency_id=self.currency_usd_id)
        inv2 = self.create_invoice(invoice_amount=20, currency_id=self.currency_usd_id)
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait_id,
            'amount': 100,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_usd.id,
        })
        payment.post()
        credit_aml = payment.move_line_ids.filtered('credit')

        # Check residual before assignation
        self.assertAlmostEquals(inv1.residual, 10)
        self.assertAlmostEquals(inv2.residual, 20)

        # Assign credit and residual
        inv1.assign_outstanding_credit(credit_aml.id)
        inv2.assign_outstanding_credit(credit_aml.id)
        self.assertAlmostEquals(inv1.residual, 0)
        self.assertAlmostEquals(inv2.residual, 0)

        # Unreconcile one invoice at a time and check residual
        credit_aml.with_context(invoice_id=inv1.id).remove_move_reconcile()
        self.assertAlmostEquals(inv1.residual, 10)
        self.assertAlmostEquals(inv2.residual, 0)
        credit_aml.with_context(invoice_id=inv2.id).remove_move_reconcile()
        self.assertAlmostEquals(inv1.residual, 10)
        self.assertAlmostEquals(inv2.residual, 20)

    def test_unreconcile_exchange(self):
        # Use case:
        # - Company currency in EUR
        # - Create 2 rates for USD:
        #   1.0 on 2018-01-01
        #   0.5 on 2018-02-01
        # - Create an invoice on 2018-01-02 of 111 USD
        # - Register a payment on 2018-02-02 of 111 USD
        # - Unreconcile the payment

        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-08-01',
            'rate': 0.5,
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id
        })
        inv = self.create_invoice(invoice_amount=111, currency_id=self.currency_usd_id)
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait_id,
            'amount': 111,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_usd.id,
            'payment_date': time.strftime('%Y') + '-08-01',
        })
        payment.post()
        credit_aml = payment.move_line_ids.filtered('credit')

        # Check residual before assignation
        self.assertAlmostEquals(inv.residual, 111)

        # Assign credit, check exchange move and residual
        inv.assign_outstanding_credit(credit_aml.id)
        self.assertEqual(len(payment.move_line_ids.mapped('full_reconcile_id').exchange_move_id), 1)
        self.assertAlmostEquals(inv.residual, 0)

        # Unreconcile invoice and check residual
        credit_aml.with_context(invoice_id=inv.id).remove_move_reconcile()
        self.assertAlmostEquals(inv.residual, 111)

    def test_revert_payment_and_reconcile(self):
        payment = self.env['account.payment'].create({
            'payment_method_id': self.inbound_payment_method.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait_id,
            'journal_id': self.bank_journal_usd.id,
            'payment_date': '2018-06-04',
            'amount': 666,
        })
        payment.post()

        self.assertEqual(len(payment.move_line_ids), 2)

        bank_line = payment.move_line_ids.filtered(lambda l: l.account_id.id == self.bank_journal_usd.default_debit_account_id.id)
        customer_line = payment.move_line_ids - bank_line

        self.assertEqual(len(bank_line), 1)
        self.assertEqual(len(customer_line), 1)
        self.assertNotEqual(bank_line.id, customer_line.id)

        self.assertEqual(bank_line.move_id.id, customer_line.move_id.id)
        move = bank_line.move_id

        # Reversing the payment's move
        reversed_move_list = move.reverse_moves('2018-06-04')
        self.assertEqual(len(reversed_move_list), 1)
        reversed_move = self.env['account.move'].browse(reversed_move_list[0])

        self.assertEqual(len(reversed_move.line_ids), 2)

        # Testing the reconciliation matching between the move lines and their reversed counterparts
        reversed_bank_line = reversed_move.line_ids.filtered(lambda l: l.account_id.id == self.bank_journal_usd.default_debit_account_id.id)
        reversed_customer_line = reversed_move.line_ids - reversed_bank_line

        self.assertEqual(len(reversed_bank_line), 1)
        self.assertEqual(len(reversed_customer_line), 1)
        self.assertNotEqual(reversed_bank_line.id, reversed_customer_line.id)
        self.assertEqual(reversed_bank_line.move_id.id, reversed_customer_line.move_id.id)

        self.assertEqual(reversed_bank_line.full_reconcile_id.id, bank_line.full_reconcile_id.id)
        self.assertEqual(reversed_customer_line.full_reconcile_id.id, customer_line.full_reconcile_id.id)

    def create_invoice_partner(self, type='out_invoice', invoice_amount=50, currency_id=None, partner_id=False):
        #we create an invoice in given currency
        invoice = self.account_invoice_model.create({'partner_id': partner_id,
            'currency_id': currency_id,
            'name': type == 'out_invoice' and 'invoice to client' or 'invoice to vendor',
            'account_id': self.account_rcv.id,
            'type': type,
            'date_invoice': time.strftime('%Y') + '-07-01',
            })
        self.account_invoice_line_model.create({'product_id': self.product.id,
            'quantity': 1,
            'price_unit': invoice_amount,
            'invoice_id': invoice.id,
            'name': 'product that cost ' + str(invoice_amount),
            'account_id': self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1).id,
        })

        #validate invoice
        invoice.action_invoice_open()
        return invoice

    def test_aged_report(self):
        AgedReport = self.env['report.account.report_agedpartnerbalance'].with_context(include_nullified_amount=True)
        account_type = ['receivable']
        report_date_to = time.strftime('%Y') + '-07-17'
        partner = self.env['res.partner'].create({'name': 'AgedPartner'})
        currency = self.env.user.company_id.currency_id

        invoice = self.create_invoice_partner(currency_id=currency.id, partner_id=partner.id)
        journal = self.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'THE'})

        statement = self.make_payment(invoice, journal, 50)

        # The report searches on the create_date to dispatch reconciled lines to report periods
        # Also, in this case, there can be only 1 partial_reconcile
        statement_partial_id = statement.move_line_ids.mapped(lambda l: l.matched_credit_ids + l.matched_debit_ids)
        self.env.cr.execute('UPDATE account_partial_reconcile SET create_date = %(date)s WHERE id = %(partial_id)s',
            {'date': report_date_to + ' 00:00:00',
             'partial_id': statement_partial_id.id})

        # Case 1: The invoice and payment are reconciled: Nothing should appear
        report_lines, total, amls = AgedReport._get_partner_move_lines(account_type, report_date_to, 'posted', 30)

        partner_lines = [line for line in report_lines if line['partner_id'] == partner.id]
        self.assertEqual(partner_lines, [], 'The aged receivable shouldn\'t have lines at this point')
        self.assertFalse(amls.get(partner.id, False), 'The aged receivable should not have amls either')

        # Case 2: The invoice and payment are not reconciled: we should have one line on the report
        # and 2 amls
        invoice.move_id.line_ids.with_context(invoice_id=invoice.id).remove_move_reconcile()
        report_lines, total, amls = AgedReport._get_partner_move_lines(account_type, report_date_to, 'posted', 30)

        partner_lines = [line for line in report_lines if line['partner_id'] == partner.id]
        self.assertEqual(partner_lines, [{'trust': 'normal', '1': 0.0, '0': 0.0, 'direction': 0.0, 'partner_id': partner.id, '3': 0.0, 'total': 0.0, 'name': 'AgedPartner', '4': 0.0, '2': 0.0}],
            'We should have a line in the report for the partner')
        self.assertEqual(len(amls[partner.id]), 2, 'We should have 2 account move lines for the partner')

        positive_line = [line for line in amls[partner.id] if line['line'].balance > 0]
        negative_line = [line for line in amls[partner.id] if line['line'].balance < 0]

        self.assertEqual(positive_line[0]['amount'], 50.0, 'The amount of the amls should be 50')
        self.assertEqual(negative_line[0]['amount'], -50.0, 'The amount of the amls should be -50')

    def test_revert_payment_and_reconcile_exchange(self):

        # A reversal of a reconciled payment which created a currency exchange entry, should create reversal moves
        # which move lines should be reconciled two by two with the original move's lines

        def _determine_debit_credit_line(move):
            line_ids_reconciliable = move.line_ids.filtered(lambda l: l.account_id.reconcile or l.account_id.internal_type == 'liquidity')
            return line_ids_reconciliable.filtered(lambda l: l.debit), line_ids_reconciliable.filtered(lambda l: l.credit)

        def _move_revert_test_pair(move, revert):
            self.assertTrue(move.line_ids)
            self.assertTrue(revert.line_ids)

            move_lines = _determine_debit_credit_line(move)
            revert_lines = _determine_debit_credit_line(revert)

            # in the case of the exchange entry, only one pair of lines will be found
            if move_lines[0] and revert_lines[1]:
                self.assertTrue(move_lines[0].full_reconcile_id.exists())
                self.assertEqual(move_lines[0].full_reconcile_id.id, revert_lines[1].full_reconcile_id.id)

            if move_lines[1] and revert_lines[0]:
                self.assertTrue(move_lines[1].full_reconcile_id.exists())
                self.assertEqual(move_lines[1].full_reconcile_id.id, revert_lines[0].full_reconcile_id.id)

        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-08-01',
            'rate': 0.5,
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id
        })
        inv = self.create_invoice(invoice_amount=111, currency_id=self.currency_usd_id)
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait_id,
            'amount': 111,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_usd.id,
            'payment_date': time.strftime('%Y') + '-08-01',
        })
        payment.post()

        credit_aml = payment.move_line_ids.filtered('credit')
        inv.assign_outstanding_credit(credit_aml.id)
        self.assertTrue(inv.state == 'paid', 'The invoice should be paid')

        exchange_reconcile = payment.move_line_ids.mapped('full_reconcile_id')
        exchange_move = exchange_reconcile.exchange_move_id
        payment_move = payment.move_line_ids[0].move_id

        reverted_payment_move = self.env['account.move'].browse(payment_move.reverse_moves(time.strftime('%Y') + '-08-01'))

        # After reversal of payment, the invoice should be open
        self.assertTrue(inv.state == 'open', 'The invoice should be open again')
        self.assertFalse(exchange_reconcile.exists())

        reverted_exchange_move = self.env['account.move'].search([('journal_id', '=', exchange_move.journal_id.id), ('ref', 'ilike', exchange_move.name)], limit=1)
        _move_revert_test_pair(payment_move, reverted_payment_move)
        _move_revert_test_pair(exchange_move, reverted_exchange_move)

    def test_aged_report_future_payment(self):
        AgedReport = self.env['report.account.report_agedpartnerbalance'].with_context(include_nullified_amount=True)
        account_type = ['receivable']
        partner = self.env['res.partner'].create({'name': 'AgedPartner'})
        currency = self.env.user.company_id.currency_id

        invoice = self.create_invoice_partner(currency_id=currency.id, partner_id=partner.id)
        journal = self.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'THE'})

        statement = self.make_payment(invoice, journal, 50)

        # Force the payment recording to take place on the invoice date
        # Although the payment due_date is in the future relative to the invoice
        # Also, in this case, there can be only 1 partial_reconcile
        statement_partial_id = statement.move_line_ids.mapped(lambda l: l.matched_credit_ids + l.matched_debit_ids)
        self.env.cr.execute('UPDATE account_partial_reconcile SET create_date = %(date)s WHERE id = %(partial_id)s',
            {'date': invoice.date_invoice,
             'partial_id': statement_partial_id.id})

        # Case 1: report date is invoice date
        # There should be an entry for the partner
        report_date_to = invoice.date_invoice
        report_lines, total, amls = AgedReport._get_partner_move_lines(account_type, report_date_to, 'posted', 30)

        partner_lines = [line for line in report_lines if line['partner_id'] == partner.id]
        self.assertEqual(partner_lines, [{
            'name': 'AgedPartner',
            'trust': 'normal',
            'partner_id': partner.id,
            '0': 0.0,
            '1': 0.0,
            '2': 0.0,
            '3': 0.0,
            '4': 0.0,
            'total': 50.0,
            'direction': 50.0,
        }], 'We should have a line in the report for the partner')
        self.assertEqual(len(amls[partner.id]), 1, 'We should have 1 account move lines for the partner')

        positive_line = [line for line in amls[partner.id] if line['line'].balance > 0]

        self.assertEqual(positive_line[0]['amount'], 50.0, 'The amount of the amls should be 50')

        # Case 2: report date between invoice date and payment date
        # There should be an entry for the partner
        # And the amount has shifted to '1-30 due'
        report_date_to = time.strftime('%Y') + '-07-08'
        report_lines, total, amls = AgedReport._get_partner_move_lines(account_type, report_date_to, 'posted', 30)

        partner_lines = [line for line in report_lines if line['partner_id'] == partner.id]
        self.assertEqual(partner_lines, [{
            'name': 'AgedPartner',
            'trust': 'normal',
            'partner_id': partner.id,
            '0': 0.0,
            '1': 0.0,
            '2': 0.0,
            '3': 0.0,
            '4': 50.0,
            'total': 50.0,
            'direction': 0.0,
        }], 'We should have a line in the report for the partner')
        self.assertEqual(len(amls[partner.id]), 1, 'We should have 1 account move lines for the partner')

        positive_line = [line for line in amls[partner.id] if line['line'].balance > 0]

        self.assertEqual(positive_line[0]['amount'], 50.0, 'The amount of the amls should be 50')

        # Case 2: report date on payment date
        # There should not be an entry for the partner
        report_date_to = time.strftime('%Y') + '-07-15'
        report_lines, total, amls = AgedReport._get_partner_move_lines(account_type, report_date_to, 'posted', 30)

        partner_lines = [line for line in report_lines if line['partner_id'] == partner.id]
        self.assertEqual(partner_lines, [], 'The aged receivable shouldn\'t have lines at this point')
        self.assertFalse(amls.get(partner.id, False), 'The aged receivable should not have amls either')

    def test_partial_reconcile_currencies_02(self):
        ####
        # Day 1: Invoice Cust/001 to customer (expressed in USD)
        # Market value of USD (day 1): 1 USD = 0.5 EUR
        # * Dr. 100 USD / 50 EUR - Accounts receivable
        # * Cr. 100 USD / 50 EUR - Revenue
        ####
        account_revenue = self.env['account.account'].search(
            [('user_type_id', '=', self.env.ref(
                'account.data_account_type_revenue').id)], limit=1)
        dest_journal_id = self.env['account.journal'].search(
            [('type', '=', 'purchase'),
             ('company_id', '=', self.env.ref('base.main_company').id)],
            limit=1)

        # Delete any old rate - to make sure that we use the ones we need.
        old_rates = self.env['res.currency.rate'].search(
            [('currency_id', '=', self.currency_usd_id)])
        old_rates.unlink()

        self.env['res.currency.rate'].create({
            'currency_id': self.currency_usd_id,
            'name': time.strftime('%Y') + '-01-01',
            'rate': 2,
        })

        invoice_cust_1 = self.account_invoice_model.create({
            'partner_id': self.partner_agrolait_id,
            'account_id': self.account_rcv.id,
            'type': 'out_invoice',
            'currency_id': self.currency_usd_id,
            'date_invoice': time.strftime('%Y') + '-01-01',
        })
        self.account_invoice_line_model.create({
            'quantity': 1.0,
            'price_unit': 100.0,
            'invoice_id': invoice_cust_1.id,
            'name': 'product that cost 100',
            'account_id': account_revenue.id,
        })
        invoice_cust_1.action_invoice_open()
        self.assertEqual(invoice_cust_1.residual_company_signed, 50.0)
        aml = invoice_cust_1.move_id.mapped('line_ids').filtered(
            lambda x: x.account_id == account_revenue)
        self.assertEqual(aml.credit, 50.0)
        #####
        # Day 2: Receive payment for half invoice Cust/1 (in USD)
        # -------------------------------------------------------
        # Market value of USD (day 2): 1 USD = 1 EUR

        # Payment transaction:
        # * Dr. 50 USD / 50 EUR - EUR Bank (valued at market price
        # at the time of receiving the money)
        # * Cr. 50 USD / 50 EUR - Accounts Receivable
        #####
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_usd_id,
            'name': time.strftime('%Y') + '-01-02',
            'rate': 1,
        })
        # register payment on invoice
        payment = self.env['account.payment'].create(
            {'payment_type': 'inbound',
             'payment_method_id': self.env.ref(
                 'account.account_payment_method_manual_in').id,
             'partner_type': 'customer',
             'partner_id': self.partner_agrolait_id,
             'amount': 50,
             'currency_id': self.currency_usd_id,
             'payment_date': time.strftime('%Y') + '-01-02',
             'journal_id': dest_journal_id.id,
             })
        payment.post()
        payment_move_line = False
        for l in payment.move_line_ids:
            if l.account_id == invoice_cust_1.account_id:
                payment_move_line = l
        invoice_cust_1.register_payment(payment_move_line)
        # We expect at this point that the invoice should still be open,
        # because they owe us still 50 CC.
        self.assertEqual(invoice_cust_1.state, 'open',
                         'Invoice is in status %s' % invoice_cust_1.state)

    def test_multiple_term_reconciliation_opw_1906665(self):
        '''Test that when registering a payment to an invoice with multiple
        payment term lines the reconciliation happens against the line
        with the earliest date_maturity
        '''

        payment_term = self.env['account.payment.term'].create({
            'name': 'Pay in 2 installments',
            'line_ids': [
                # Pay 50% immediately
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 50,
                }),
                # Pay the rest after 14 days
                (0, 0, {
                    'value': 'balance',
                    'days': 14,
                })
            ],
        })

        # can't use self.create_invoice because it validates and we need to set payment_term_id
        invoice = self.account_invoice_model.create({
            'partner_id': self.partner_agrolait_id,
            'payment_term_id': payment_term.id,
            'currency_id': self.currency_usd_id,
            'name': 'Multiple payment terms',
            'account_id': self.account_rcv.id,
            'type': 'out_invoice',
            'date_invoice': time.strftime('%Y') + '-07-01',
        })
        self.account_invoice_line_model.create({
            'product_id': self.product.id,
            'quantity': 1,
            'price_unit': 50,
            'invoice_id': invoice.id,
            'name': self.product.display_name,
            'account_id': self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1).id,
        })

        invoice.action_invoice_open()

        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait_id,
            'amount': 25,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_usd.id,
        })
        payment.post()

        invoice.assign_outstanding_credit(payment.move_line_ids.filtered('credit').id)

        receivable_lines = invoice.move_id.line_ids.filtered(lambda line: line.account_id == self.account_rcv).sorted('date_maturity')[0]
        self.assertTrue(receivable_lines.matched_credit_ids)

    def test_reconciliation_cash_basis01(self):
        # Simulates an expense made up by 2 lines
        # one is subject to a cash basis tax
        # the other is not subject to tax

        company = self.env.ref('base.main_company')
        company.tax_cash_basis_journal_id = self.cash_basis_journal

        AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False)

        # Purchase
        purchase_move = self.env['account.move'].create({
            'name': 'purchase',
            'journal_id': self.purchase_journal.id,
        })

        purchase_payable_line0 = AccountMoveLine.create({
            'account_id': self.account_rsa.id,
            'credit': 100,
            'move_id': purchase_move.id,
        })
        purchase_payable_line1 = AccountMoveLine.create({
            'account_id': self.account_rsa.id,
            'credit': 50,
            'move_id': purchase_move.id,
        })
        AccountMoveLine.create({
            'name': 'expensNoTax',
            'account_id': self.expense_account.id,
            'debit': 50,
            'move_id': purchase_move.id,
        })
        AccountMoveLine.create({
            'name': 'expenseTaxed',
            'account_id': self.expense_account.id,
            'debit': 83.33,
            'move_id': purchase_move.id,
            'tax_ids': [(4, self.tax_cash_basis.id, False)],
        })
        tax_line = AccountMoveLine.create({
            'name': 'TaxLine',
            'account_id': self.tax_waiting_account.id,
            'debit': 16.67,
            'move_id': purchase_move.id,
            'tax_line_id': self.tax_cash_basis.id,
        })
        purchase_move.post()

        # Payment Move
        payment_move = self.env['account.move'].create({
            'name': 'payment',
            'journal_id': self.bank_journal_euro.id,
        })
        payment_payable_line = AccountMoveLine.create({
            'account_id': self.account_rsa.id,
            'debit': 150,
            'move_id': payment_move.id,
        })
        AccountMoveLine.create({
            'account_id': self.account_euro.id,
            'credit': 150,
            'move_id': payment_move.id,
        })
        payment_move.post()

        to_reconcile = (purchase_move + payment_move).mapped('line_ids').filtered(lambda l: l.account_id.internal_type == 'payable')
        to_reconcile.reconcile()

        cash_basis_moves = self.env['account.move'].search([('journal_id', '=', self.cash_basis_journal.id)])

        self.assertEqual(len(cash_basis_moves), 2)
        self.assertTrue(cash_basis_moves.exists())

        # check reconciliation in Payable account
        self.assertTrue(purchase_payable_line0.full_reconcile_id.exists())
        self.assertEqual(purchase_payable_line0.full_reconcile_id.reconciled_line_ids,
            purchase_payable_line0 + purchase_payable_line1 + payment_payable_line)

        cash_basis_aml_ids = cash_basis_moves.mapped('line_ids')
        # check reconciliation in the tax waiting account
        self.assertTrue(tax_line.full_reconcile_id.exists())
        self.assertEqual(tax_line.full_reconcile_id.reconciled_line_ids,
            cash_basis_aml_ids.filtered(lambda l: l.account_id == self.tax_waiting_account) + tax_line)

        self.assertEqual(len(cash_basis_aml_ids), 8)

        # check amounts
        cash_basis_move1 = cash_basis_moves.filtered(lambda m: m.amount == 33.34)
        cash_basis_move2 = cash_basis_moves.filtered(lambda m: m.amount == 66.66)

        self.assertTrue(cash_basis_move1.exists())
        self.assertTrue(cash_basis_move2.exists())

        # For first move
        move_lines = cash_basis_move1.line_ids
        base_amount_tax_lines = move_lines.filtered(lambda l: l.account_id == self.tax_base_amount_account)
        self.assertEqual(len(base_amount_tax_lines), 2)
        self.assertAlmostEqual(sum(base_amount_tax_lines.mapped('credit')), 27.78)
        self.assertAlmostEqual(sum(base_amount_tax_lines.mapped('debit')), 27.78)

        self.assertAlmostEqual((move_lines - base_amount_tax_lines).filtered(lambda l: l.account_id == self.tax_waiting_account).credit,
            5.56)
        self.assertAlmostEqual((move_lines - base_amount_tax_lines).filtered(lambda l: l.account_id == self.tax_final_account).debit,
            5.56)

        # For second move
        move_lines = cash_basis_move2.line_ids
        base_amount_tax_lines = move_lines.filtered(lambda l: l.account_id == self.tax_base_amount_account)
        self.assertEqual(len(base_amount_tax_lines), 2)
        self.assertAlmostEqual(sum(base_amount_tax_lines.mapped('credit')), 55.55)
        self.assertAlmostEqual(sum(base_amount_tax_lines.mapped('debit')), 55.55)

        self.assertAlmostEqual((move_lines - base_amount_tax_lines).filtered(lambda l: l.account_id == self.tax_waiting_account).credit,
            11.11)
        self.assertAlmostEqual((move_lines - base_amount_tax_lines).filtered(lambda l: l.account_id == self.tax_final_account).debit,
            11.11)

    def test_reconciliation_cash_basis02(self):
        # Simulates an invoice made up by 2 lines
        # both subjected to cash basis taxes
        # with 2 payment terms
        # And partial payment not martching any payment term

        company = self.env.ref('base.main_company')
        company.tax_cash_basis_journal_id = self.cash_basis_journal
        tax_cash_basis10percent = self.tax_cash_basis.copy({'amount': 10})
        tax_waiting_account10 = self.tax_waiting_account.copy({
            'name': 'TAX WAIT 10',
            'code': 'TWAIT1',
        })


        AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False)

        # Purchase
        purchase_move = self.env['account.move'].create({
            'name': 'invoice',
            'journal_id': self.purchase_journal.id,
        })

        purchase_payable_line0 = AccountMoveLine.create({
            'account_id': self.account_rsa.id,
            'credit': 105,
            'move_id': purchase_move.id,
        })
        purchase_payable_line1 = AccountMoveLine.create({
            'account_id': self.account_rsa.id,
            'credit': 50,
            'move_id': purchase_move.id,
        })
        AccountMoveLine.create({
            'name': 'expenseTaxed 10%',
            'account_id': self.expense_account.id,
            'debit': 50,
            'move_id': purchase_move.id,
            'tax_ids': [(4, tax_cash_basis10percent.id, False)],
        })
        tax_line0 = AccountMoveLine.create({
            'name': 'TaxLine0',
            'account_id': tax_waiting_account10.id,
            'debit': 5,
            'move_id': purchase_move.id,
            'tax_line_id': tax_cash_basis10percent.id,
        })
        AccountMoveLine.create({
            'name': 'expenseTaxed 20%',
            'account_id': self.expense_account.id,
            'debit': 83.33,
            'move_id': purchase_move.id,
            'tax_ids': [(4, self.tax_cash_basis.id, False)],
        })
        tax_line1 = AccountMoveLine.create({
            'name': 'TaxLine1',
            'account_id': self.tax_waiting_account.id,
            'debit': 16.67,
            'move_id': purchase_move.id,
            'tax_line_id': self.tax_cash_basis.id,
        })
        purchase_move.post()

        # Payment Move
        payment_move0 = self.env['account.move'].create({
            'name': 'payment',
            'journal_id': self.bank_journal_euro.id,
        })
        payment_payable_line0 = AccountMoveLine.create({
            'account_id': self.account_rsa.id,
            'debit': 40,
            'move_id': payment_move0.id,
        })
        AccountMoveLine.create({
            'account_id': self.account_euro.id,
            'credit': 40,
            'move_id': payment_move0.id,
        })
        payment_move0.post()

        # Payment Move
        payment_move1 = self.env['account.move'].create({
            'name': 'payment',
            'journal_id': self.bank_journal_euro.id,
        })
        payment_payable_line1 = AccountMoveLine.create({
            'account_id': self.account_rsa.id,
            'debit': 115,
            'move_id': payment_move1.id,
        })
        AccountMoveLine.create({
            'account_id': self.account_euro.id,
            'credit': 115,
            'move_id': payment_move1.id,
        })
        payment_move1.post()

        (purchase_move + payment_move0).mapped('line_ids').filtered(lambda l: l.account_id.internal_type == 'payable').reconcile()
        (purchase_move + payment_move1).mapped('line_ids').filtered(lambda l: l.account_id.internal_type == 'payable').reconcile()

        cash_basis_moves = self.env['account.move'].search([('journal_id', '=', self.cash_basis_journal.id)])

        self.assertEqual(len(cash_basis_moves), 3)
        self.assertTrue(cash_basis_moves.exists())

        # check reconciliation in Payable account
        self.assertTrue(purchase_payable_line0.full_reconcile_id.exists())
        self.assertEqual(purchase_payable_line0.full_reconcile_id.reconciled_line_ids,
            purchase_payable_line0 + purchase_payable_line1 + payment_payable_line0 + payment_payable_line1)

        cash_basis_aml_ids = cash_basis_moves.mapped('line_ids')

        # check reconciliation in the tax waiting account
        self.assertTrue(tax_line0.full_reconcile_id.exists())
        self.assertEqual(tax_line0.full_reconcile_id.reconciled_line_ids,
            cash_basis_aml_ids.filtered(lambda l: l.account_id == tax_waiting_account10) + tax_line0)

        self.assertTrue(tax_line1.full_reconcile_id.exists())
        self.assertEqual(tax_line1.full_reconcile_id.reconciled_line_ids,
            cash_basis_aml_ids.filtered(lambda l: l.account_id == self.tax_waiting_account) + tax_line1)

        self.assertEqual(len(cash_basis_aml_ids), 24)

        # check amounts
        expected_move_amounts = [
            {'base_20': 56.45, 'tax_20': 11.29, 'base_10': 33.87, 'tax_10': 3.39},
            {'base_20': 21.50, 'tax_20': 4.30, 'base_10': 12.90, 'tax_10': 1.29},
            {'base_20': 5.38, 'tax_20': 1.08, 'base_10': 3.23, 'tax_10': 0.32},
        ]

        index = 0
        for cb_move in cash_basis_moves.sorted('amount', reverse=True):
            expected = expected_move_amounts[index]
            move_lines = cb_move.line_ids
            base_amount_tax_lines20per = move_lines.filtered(lambda l: l.account_id == self.tax_base_amount_account and '20%' in l.name)
            base_amount_tax_lines10per = move_lines.filtered(lambda l: l.account_id == self.tax_base_amount_account and '10%' in l.name)
            self.assertEqual(len(base_amount_tax_lines20per), 2)

            self.assertAlmostEqual(sum(base_amount_tax_lines20per.mapped('credit')), expected['base_20'])
            self.assertAlmostEqual(sum(base_amount_tax_lines20per.mapped('debit')), expected['base_20'])

            self.assertEqual(len(base_amount_tax_lines10per), 2)
            self.assertAlmostEqual(sum(base_amount_tax_lines10per.mapped('credit')), expected['base_10'])
            self.assertAlmostEqual(sum(base_amount_tax_lines10per.mapped('debit')), expected['base_10'])

            self.assertAlmostEqual(
                (move_lines - base_amount_tax_lines20per - base_amount_tax_lines10per)
                .filtered(lambda l: l.account_id == self.tax_waiting_account).credit,
                expected['tax_20']
            )
            self.assertAlmostEqual(
                (move_lines - base_amount_tax_lines20per - base_amount_tax_lines10per)
                .filtered(lambda l: 'TaxLine1' in l.name).debit,
                expected['tax_20']
            )

            self.assertAlmostEqual(
                (move_lines - base_amount_tax_lines20per - base_amount_tax_lines10per)
                .filtered(lambda l: l.account_id == tax_waiting_account10).credit,
                expected['tax_10']
            )
            self.assertAlmostEqual(
                (move_lines - base_amount_tax_lines20per - base_amount_tax_lines10per)
                .filtered(lambda l: 'TaxLine0' in l.name).debit,
                expected['tax_10']
            )
            index += 1

    def test_reconciliation_cash_basis_fx_01(self):
        """
        Company's Currency EUR

        Having issued an invoice at date Nov-21-2018 as:

        Accounts         Amount Currency         Debit(EUR)       Credit(EUR)
        ---------------------------------------------------------------------
        Expenses            5,301.00 USD         106,841.65              0.00
        Taxes                 848.16 USD          17,094.66              0.00
            Payables       -6,149.16 USD               0.00        123,936.31

        On Dec-20-2018 user issues an FX Journal Entry as:

        Accounts         Amount Currency         Debit(EUR)       Credit(EUR)
        ---------------------------------------------------------------------
        Payables                0.00 USD             167.86             0.00
            FX Gains            0.00 USD               0.00           167.86

        On Same day user records a payment for:

        Accounts         Amount Currency         Debit(EUR)       Credit(EUR)
        ---------------------------------------------------------------------
        Payables            6,149.16 USD         123,768.45              0.00
            Bank           -6,149.16 USD               0.00        123,768.45

        And then reconciles the Payables Items which shall render only one Tax
        Cash Basis Journal Entry because of the actual payment, i.e.
        amount_currency != 0:

        Accounts         Amount Currency         Debit(EUR)       Credit(EUR)
        ---------------------------------------------------------------------
        Tax Base Acc.           0.00 USD         106,841.65              0.00
            Tax Base Acc.       0.00 USD               0.00        106,841.65
        Creditable Taxes      848.16 USD          17,094.66              0.00
            Taxes            -848.16 USD               0.00         17,094.66
        """

        company = self.env.ref('base.main_company')
        company.country_id = self.ref('base.us')
        company.tax_cash_basis_journal_id = self.cash_basis_journal

        aml_obj = self.env['account.move.line'].with_context(
            check_move_validity=False)

        # Purchase
        purchase_move = self.env['account.move'].create({
            'name': 'purchase',
            'journal_id': self.purchase_journal.id,
        })

        aml_obj.create({
            'name': 'expenseTaxed',
            'account_id': self.expense_account.id,
            'debit': 106841.65,
            'move_id': purchase_move.id,
            'tax_ids': [(4, self.tax_cash_basis.id, False)],
            'currency_id': self.currency_usd_id,
            'amount_currency': 5301.00,
        })
        aml_obj.create({
            'name': 'TaxLine',
            'account_id': self.tax_waiting_account.id,
            'debit': 17094.66,
            'move_id': purchase_move.id,
            'tax_line_id': self.tax_cash_basis.id,
            'currency_id': self.currency_usd_id,
            'amount_currency': 848.16,
        })
        purchase_payable_line0 = aml_obj.create({
            'name': 'Payable',
            'account_id': self.account_rsa.id,
            'credit': 123936.31,
            'move_id': purchase_move.id,
            'currency_id': self.currency_usd_id,
            'amount_currency': -6149.16,
        })
        purchase_move.post()

        # FX 01 Move
        fx_move_01 = self.env['account.move'].create({
            'name': 'FX 01',
            'journal_id': self.fx_journal.id,
        })
        fx_01_payable_line = aml_obj.create({
            'account_id': self.account_rsa.id,
            'debit': 167.86,
            'move_id': fx_move_01.id,
            'currency_id': self.currency_usd_id,
            'amount_currency': 0.00,
        })
        aml_obj.create({
            'account_id': self.diff_income_account.id,
            'credit': 167.86,
            'move_id': fx_move_01.id,
            'currency_id': self.currency_usd_id,
            'amount_currency': 0.00,
        })
        fx_move_01.post()

        # Payment Move
        payment_move = self.env['account.move'].create({
            'name': 'payment',
            'journal_id': self.bank_journal_usd.id,
        })
        payment_payable_line = aml_obj.create({
            'account_id': self.account_rsa.id,
            'debit': 123768.45,
            'move_id': payment_move.id,
            'currency_id': self.currency_usd_id,
            'amount_currency': 6149.16,
        })
        aml_obj.create({
            'account_id': self.account_usd.id,
            'credit': 123768.45,
            'move_id': payment_move.id,
            'currency_id': self.currency_usd_id,
            'amount_currency': -6149.16,
        })
        payment_move.post()

        to_reconcile = (
            (purchase_move + payment_move + fx_move_01).mapped('line_ids')
            .filtered(lambda l: l.account_id.internal_type == 'payable'))
        to_reconcile.reconcile()

        # check reconciliation in Payable account
        self.assertTrue(purchase_payable_line0.full_reconcile_id.exists())
        self.assertEqual(
            purchase_payable_line0.full_reconcile_id.reconciled_line_ids,
            purchase_payable_line0 + fx_01_payable_line + payment_payable_line)

        # check cash basis
        cash_basis_moves = self.env['account.move'].search(
            [('journal_id', '=', self.cash_basis_journal.id)])

        self.assertEqual(len(cash_basis_moves), 1)

        cash_basis_aml_ids = cash_basis_moves.mapped('line_ids')
        self.assertEqual(len(cash_basis_aml_ids), 4)

        # check amounts
        cash_basis_move1 = cash_basis_moves.filtered(
            lambda m: m.amount == 123936.31)

        self.assertTrue(cash_basis_move1.exists())

        # For first move
        move_lines = cash_basis_move1.line_ids
        base_amount_tax_lines = move_lines.filtered(
            lambda l: l.account_id == self.tax_base_amount_account)
        self.assertEqual(len(base_amount_tax_lines), 2)
        self.assertAlmostEqual(
            sum(base_amount_tax_lines.mapped('credit')), 106841.65)
        self.assertAlmostEqual(
            sum(base_amount_tax_lines.mapped('debit')), 106841.65)

        self.assertAlmostEqual(
            (move_lines - base_amount_tax_lines)
            .filtered(lambda l: l.account_id == self.tax_waiting_account)
            .credit, 17094.66)
        self.assertAlmostEqual(
            (move_lines - base_amount_tax_lines)
            .filtered(lambda l: l.account_id == self.tax_final_account)
            .debit, 17094.66)

    def test_reconciliation_cash_basis_fx_02(self):
        """
        Company's Currency EUR

        Having issued an invoice at date Nov-21-2018 as:

        Accounts         Amount Currency         Debit(EUR)       Credit(EUR)
        ---------------------------------------------------------------------
        Expenses            5,301.00 USD         106,841.65              0.00
        Taxes                 848.16 USD          17,094.66              0.00
            Payables       -6,149.16 USD               0.00        123,936.31

        On Nov-30-2018 user issues an FX Journal Entry as:

        Accounts         Amount Currency         Debit(EUR)       Credit(EUR)
        ---------------------------------------------------------------------
        FX Losses               0.00 USD           1.572.96             0.00
            Payables            0.00 USD               0.00         1.572.96

        On Dec-20-2018 user issues an FX Journal Entry as:

        Accounts         Amount Currency         Debit(EUR)       Credit(EUR)
        ---------------------------------------------------------------------
        Payables                0.00 USD           1.740.82             0.00
            FX Gains            0.00 USD               0.00         1.740.82

        On Same day user records a payment for:

        Accounts         Amount Currency         Debit(EUR)       Credit(EUR)
        ---------------------------------------------------------------------
        Payables            6,149.16 USD         123,768.45              0.00
            Bank           -6,149.16 USD               0.00        123,768.45

        And then reconciles the Payables Items which shall render only one Tax
        Cash Basis Journal Entry because of the actual payment, i.e.
        amount_currency != 0:

        Accounts         Amount Currency         Debit(EUR)       Credit(EUR)
        ---------------------------------------------------------------------
        Tax Base Acc.           0.00 USD         106,841.65              0.00
            Tax Base Acc.       0.00 USD               0.00        106,841.65
        Creditable Taxes      848.16 USD          17,094.66              0.00
            Taxes            -848.16 USD               0.00         17,094.66
        """

        company = self.env.ref('base.main_company')
        company.country_id = self.ref('base.us')
        company.tax_cash_basis_journal_id = self.cash_basis_journal

        aml_obj = self.env['account.move.line'].with_context(
            check_move_validity=False)

        # Purchase
        purchase_move = self.env['account.move'].create({
            'name': 'purchase',
            'journal_id': self.purchase_journal.id,
        })

        aml_obj.create({
            'name': 'expenseTaxed',
            'account_id': self.expense_account.id,
            'debit': 106841.65,
            'move_id': purchase_move.id,
            'tax_ids': [(4, self.tax_cash_basis.id, False)],
            'currency_id': self.currency_usd_id,
            'amount_currency': 5301.00,
        })
        aml_obj.create({
            'name': 'TaxLine',
            'account_id': self.tax_waiting_account.id,
            'debit': 17094.66,
            'move_id': purchase_move.id,
            'tax_line_id': self.tax_cash_basis.id,
            'currency_id': self.currency_usd_id,
            'amount_currency': 848.16,
        })
        purchase_payable_line0 = aml_obj.create({
            'name': 'Payable',
            'account_id': self.account_rsa.id,
            'credit': 123936.31,
            'move_id': purchase_move.id,
            'currency_id': self.currency_usd_id,
            'amount_currency': -6149.16,
        })
        purchase_move.post()

        # FX 01 Move
        fx_move_01 = self.env['account.move'].create({
            'name': 'FX 01',
            'journal_id': self.fx_journal.id,
        })
        fx_01_payable_line = aml_obj.create({
            'account_id': self.account_rsa.id,
            'credit': 1572.96,
            'move_id': fx_move_01.id,
            'currency_id': self.currency_usd_id,
            'amount_currency': 0.00,
        })
        aml_obj.create({
            'account_id': self.diff_expense_account.id,
            'debit': 1572.96,
            'move_id': fx_move_01.id,
            'currency_id': self.currency_usd_id,
            'amount_currency': 0.00,
        })
        fx_move_01.post()

        # FX 02 Move
        fx_move_02 = self.env['account.move'].create({
            'name': 'FX 02',
            'journal_id': self.fx_journal.id,
        })
        fx_02_payable_line = aml_obj.create({
            'account_id': self.account_rsa.id,
            'debit': 1740.82,
            'move_id': fx_move_02.id,
            'currency_id': self.currency_usd_id,
            'amount_currency': 0.00,
        })
        aml_obj.create({
            'account_id': self.diff_income_account.id,
            'credit': 1740.82,
            'move_id': fx_move_02.id,
            'currency_id': self.currency_usd_id,
            'amount_currency': 0.00,
        })
        fx_move_02.post()

        # Payment Move
        payment_move = self.env['account.move'].create({
            'name': 'payment',
            'journal_id': self.bank_journal_usd.id,
        })
        payment_payable_line = aml_obj.create({
            'account_id': self.account_rsa.id,
            'debit': 123768.45,
            'move_id': payment_move.id,
            'currency_id': self.currency_usd_id,
            'amount_currency': 6149.16,
        })
        aml_obj.create({
            'account_id': self.account_usd.id,
            'credit': 123768.45,
            'move_id': payment_move.id,
            'currency_id': self.currency_usd_id,
            'amount_currency': -6149.16,
        })
        payment_move.post()

        to_reconcile = (
            (purchase_move + payment_move + fx_move_01 + fx_move_02)
            .mapped('line_ids')
            .filtered(lambda l: l.account_id.internal_type == 'payable'))
        to_reconcile.reconcile()

        # check reconciliation in Payable account
        self.assertTrue(purchase_payable_line0.full_reconcile_id.exists())
        self.assertEqual(
            purchase_payable_line0.full_reconcile_id.reconciled_line_ids,
            purchase_payable_line0 + fx_01_payable_line + fx_02_payable_line +
            payment_payable_line)

        # check cash basis
        cash_basis_moves = self.env['account.move'].search(
            [('journal_id', '=', self.cash_basis_journal.id)])

        self.assertEqual(len(cash_basis_moves), 1)

        cash_basis_aml_ids = cash_basis_moves.mapped('line_ids')
        self.assertEqual(len(cash_basis_aml_ids), 4)

        # check amounts
        cash_basis_move1 = cash_basis_moves.filtered(
            lambda m: m.amount == 123936.31)

        self.assertTrue(cash_basis_move1.exists())

        # For first move
        move_lines = cash_basis_move1.line_ids
        base_amount_tax_lines = move_lines.filtered(
            lambda l: l.account_id == self.tax_base_amount_account)
        self.assertEqual(len(base_amount_tax_lines), 2)
        self.assertAlmostEqual(
            sum(base_amount_tax_lines.mapped('credit')), 106841.65)
        self.assertAlmostEqual(
            sum(base_amount_tax_lines.mapped('debit')), 106841.65)

        self.assertAlmostEqual(
            (move_lines - base_amount_tax_lines)
            .filtered(lambda l: l.account_id == self.tax_waiting_account)
            .credit, 17094.66)
        self.assertAlmostEqual(
            (move_lines - base_amount_tax_lines)
            .filtered(lambda l: l.account_id == self.tax_final_account)
            .debit, 17094.66)

    def test_reconciliation_cash_basis_revert(self):
        company = self.env.ref('base.main_company')
        company.tax_cash_basis_journal_id = self.cash_basis_journal
        tax_cash_basis10percent = self.tax_cash_basis.copy({'amount': 10})
        self.tax_waiting_account.reconcile = True
        tax_waiting_account10 = self.tax_waiting_account.copy({
            'name': 'TAX WAIT 10',
            'code': 'TWAIT1',
        })

        AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False)

        # Purchase
        purchase_move = self.env['account.move'].create({
            'name': 'invoice',
            'journal_id': self.purchase_journal.id,
        })

        purchase_payable_line0 = AccountMoveLine.create({
            'account_id': self.account_rsa.id,
            'credit': 175,
            'move_id': purchase_move.id,
        })

        AccountMoveLine.create({
            'name': 'expenseTaxed 10%',
            'account_id': self.expense_account.id,
            'debit': 50,
            'move_id': purchase_move.id,
            'tax_ids': [(4, tax_cash_basis10percent.id, False)],
        })
        tax_line0 = AccountMoveLine.create({
            'name': 'TaxLine0',
            'account_id': tax_waiting_account10.id,
            'debit': 5,
            'move_id': purchase_move.id,
            'tax_line_id': tax_cash_basis10percent.id,
        })
        AccountMoveLine.create({
            'name': 'expenseTaxed 20%',
            'account_id': self.expense_account.id,
            'debit': 100,
            'move_id': purchase_move.id,
            'tax_ids': [(4, self.tax_cash_basis.id, False)],
        })
        tax_line1 = AccountMoveLine.create({
            'name': 'TaxLine1',
            'account_id': self.tax_waiting_account.id,
            'debit': 20,
            'move_id': purchase_move.id,
            'tax_line_id': self.tax_cash_basis.id,
        })
        purchase_move.post()

        reverted = self.env['account.move'].browse(purchase_move.reverse_moves())
        self.assertTrue(reverted.exists())

        for inv_line in [purchase_payable_line0, tax_line0, tax_line1]:
            self.assertTrue(inv_line.full_reconcile_id.exists())
            reverted_expected = reverted.line_ids.filtered(lambda l: l.account_id == inv_line.account_id)
            self.assertEqual(len(reverted_expected), 1)
            self.assertEqual(reverted_expected.full_reconcile_id, inv_line.full_reconcile_id)

    def test_reconciliation_cash_basis_foreign_currency_low_values(self):
        journal = self.env['account.journal'].create({
            'name': 'Bank', 'type': 'bank', 'code': 'THE',
            'currency_id': self.currency_usd_id,
        })
        usd = self.env['res.currency'].browse(self.currency_usd_id)
        usd.rate_ids.unlink()
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y-01-01'),
            'rate': 1/17.0,
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id,
        })
        invoice = self.create_invoice(
            type='out_invoice', invoice_amount=50,
            currency_id=self.currency_usd_id)
        invoice.journal_id.update_posted = True
        invoice.action_cancel()
        invoice.state = 'draft'
        invoice.invoice_line_ids.write({
            'invoice_line_tax_ids': [(6, 0, [self.tax_cash_basis.id])]})
        invoice.compute_taxes()
        invoice.action_invoice_open()

        self.assertTrue(invoice.currency_id != self.env.user.company_id.currency_id)

        # First Payment
        payment0 = self.make_payment(invoice, journal, invoice.amount_total - 0.01)
        self.assertEqual(invoice.residual, 0.01)

        tax_waiting_line = invoice.move_id.line_ids.filtered(lambda l: l.account_id == self.tax_waiting_account)
        self.assertFalse(tax_waiting_line.reconciled)

        move_caba0 = tax_waiting_line.matched_debit_ids.debit_move_id.move_id
        self.assertTrue(move_caba0.exists())
        self.assertEqual(move_caba0.journal_id, self.env.user.company_id.tax_cash_basis_journal_id)

        pay_receivable_line0 = payment0.move_line_ids.filtered(lambda l: l.account_id == self.account_rcv)
        self.assertTrue(pay_receivable_line0.reconciled)
        self.assertEqual(pay_receivable_line0.matched_debit_ids, move_caba0.tax_cash_basis_rec_id)

        # Second Payment
        payment1 = self.make_payment(invoice, journal, 0.01)
        self.assertEqual(invoice.residual, 0)
        self.assertEqual(invoice.state, 'paid')

        self.assertTrue(tax_waiting_line.reconciled)
        move_caba1 = tax_waiting_line.matched_debit_ids.mapped('debit_move_id').mapped('move_id').filtered(lambda m: m != move_caba0)
        self.assertEqual(len(move_caba1.exists()), 1)
        self.assertEqual(move_caba1.journal_id, self.env.user.company_id.tax_cash_basis_journal_id)

        pay_receivable_line1 = payment1.move_line_ids.filtered(lambda l: l.account_id == self.account_rcv)
        self.assertTrue(pay_receivable_line1.reconciled)
        self.assertEqual(pay_receivable_line1.matched_debit_ids, move_caba1.tax_cash_basis_rec_id)

    def test_reconciliation_with_currency(self):
        #reconciliation on an account having a foreign currency being
        #the same as the company one
        account_rcv = self.account_rcv
        account_rcv.currency_id = self.currency_euro_id
        aml_obj = self.env['account.move.line'].with_context(
            check_move_validity=False)
        general_move1 = self.env['account.move'].create({
            'name': 'general1',
            'journal_id': self.general_journal.id,
        })
        aml_obj.create({
            'name': 'debit1',
            'account_id': account_rcv.id,
            'debit': 11,
            'move_id': general_move1.id,
        })
        aml_obj.create({
            'name': 'credit1',
            'account_id': self.account_rsa.id,
            'credit': 11,
            'move_id': general_move1.id,
        })
        general_move1.post()
        general_move2 = self.env['account.move'].create({
            'name': 'general2',
            'journal_id': self.general_journal.id,
        })
        aml_obj.create({
            'name': 'credit2',
            'account_id': account_rcv.id,
            'credit': 10,
            'move_id': general_move2.id,
        })
        aml_obj.create({
            'name': 'debit2',
            'account_id': self.account_rsa.id,
            'debit': 10,
            'move_id': general_move2.id,
        })
        general_move2.post()
        general_move3 = self.env['account.move'].create({
            'name': 'general3',
            'journal_id': self.general_journal.id,
        })
        aml_obj.create({
            'name': 'credit3',
            'account_id': account_rcv.id,
            'credit': 1,
            'move_id': general_move3.id,
        })
        aml_obj.create({
            'name': 'debit3',
            'account_id': self.account_rsa.id,
            'debit': 1,
            'move_id': general_move3.id,
        })
        general_move3.post()
        to_reconcile = ((general_move1 + general_move2 + general_move3)
            .mapped('line_ids')
            .filtered(lambda l: l.account_id.id == account_rcv.id))
        to_reconcile.reconcile()
        for aml in to_reconcile:
            self.assertEqual(aml.amount_residual, 0.0)
