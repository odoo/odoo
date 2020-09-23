from odoo import api, fields
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.exceptions import UserError
from odoo.tests import Form, tagged
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
        self.acc_bank_stmt_model = self.env['account.bank.statement']
        self.acc_bank_stmt_line_model = self.env['account.bank.statement.line']
        self.res_currency_model = self.registry('res.currency')
        self.res_currency_rate_model = self.registry('res.currency.rate')

        self.partner_agrolait = self.env.ref("base.res_partner_2")
        self.partner_agrolait_id = self.partner_agrolait.id
        self.currency_swiss_id = self.env.ref("base.CHF").id
        self.currency_usd_id = self.env.ref("base.USD").id
        self.currency_euro_id = self.env.ref("base.EUR").id
        company = self.env.ref('base.main_company')
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", [self.currency_euro_id, company.id])
        self.account_rcv = self.partner_agrolait.property_account_receivable_id or self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_receivable').id)], limit=1)
        self.account_rsa = self.partner_agrolait.property_account_payable_id or self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_payable').id)], limit=1)
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
        self.tax_tag_base = self.env['account.account.tag'].create({
            'name': "Base tag",
            'applicability': 'taxes',
            'country_id': company.country_id.id,
        })

        self.tax_tag_tax = self.env['account.account.tag'].create({
            'name': "Tax tag",
            'applicability': 'taxes',
            'country_id': company.country_id.id,
        })

        self.tax_cash_basis = self.env['account.tax'].create({
            'name': 'cash basis 20%',
            'type_tax_use': 'purchase',
            'company_id': company.id,
            'amount': 20,
            'tax_exigibility': 'on_payment',
            'cash_basis_transition_account_id': self.tax_waiting_account.id,
            'cash_basis_base_account_id': self.tax_base_amount_account.id,
            'invoice_repartition_line_ids': [
                    (0,0, {
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': [(6, 0, self.tax_tag_base.ids)],
                    }),

                    (0,0, {
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': self.tax_final_account.id,
                        'tag_ids': [(6, 0, self.tax_tag_tax.ids)],
                    }),
                ],
            'refund_repartition_line_ids': [
                    (0,0, {
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),

                    (0,0, {
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': self.tax_final_account.id,
                    }),
                ],
        })

    def _create_invoice(self, type='out_invoice', invoice_amount=50, currency_id=None, partner_id=None, date_invoice=None, payment_term_id=False, auto_validate=False, tax=None):
        date_invoice = date_invoice or time.strftime('%Y') + '-07-01'
        invoice_vals = {
            'type': type,
            'partner_id': partner_id or self.partner_agrolait_id,
            'invoice_date': date_invoice,
            'date': date_invoice,
            'invoice_line_ids': [(0, 0, {
                'name': 'product that cost %s' % invoice_amount,
                'quantity': 1,
                'price_unit': invoice_amount,
                'tax_ids': [(6, 0, tax and tax.ids or [])],
            })]
        }

        if payment_term_id:
            invoice_vals['invoice_payment_term_id'] = payment_term_id

        if currency_id:
            invoice_vals['currency_id'] = currency_id

        invoice = self.env['account.move'].with_context(default_type=type).create(invoice_vals)
        if auto_validate:
            invoice.post()
        return invoice

    def create_invoice(self, type='out_invoice', invoice_amount=50, currency_id=None):
        return self._create_invoice(type=type, invoice_amount=invoice_amount, currency_id=currency_id, auto_validate=True)

    def create_invoice_partner(self, type='out_invoice', invoice_amount=50, currency_id=None, partner_id=False, payment_term_id=False):
        return self._create_invoice(
            type=type,
            invoice_amount=invoice_amount,
            currency_id=currency_id,
            partner_id=partner_id,
            payment_term_id=payment_term_id,
            auto_validate=True
        )

    def make_payment(self, invoice_record, bank_journal, amount=0.0, amount_currency=0.0, currency_id=None):
        bank_stmt = self.acc_bank_stmt_model.create({
            'journal_id': bank_journal.id,
            'date': time.strftime('%Y') + '-07-15',
            'name': 'payment' + invoice_record.name
        })

        bank_stmt_line = self.acc_bank_stmt_line_model.create({'name': 'payment',
            'statement_id': bank_stmt.id,
            'partner_id': self.partner_agrolait_id,
            'amount': amount,
            'amount_currency': amount_currency,
            'currency_id': currency_id,
            'date': time.strftime('%Y') + '-07-15',
        })
        line_id = invoice_record.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
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
            {'debit': 0.0,      'credit': 30.0,     'amount_currency': -42, 'currency_id': self.currency_usd_id},
            {'debit': 30.0,     'credit': 0.0,      'amount_currency': 42,  'currency_id': self.currency_usd_id},
        ])
        self.assertRecordValues(supplier_move_lines, [
            {'debit': 30.0,     'credit': 0.0,      'amount_currency': 42,  'currency_id': self.currency_usd_id},
            {'debit': 0.0,      'credit': 30.0,     'amount_currency': -42, 'currency_id': self.currency_usd_id},
        ])

    def test_statement_usd_invoice_usd_transaction_usd(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_usd, 50, 0, False)
        self.assertRecordValues(customer_move_lines, [
            {'debit': 0.0,      'credit': 32.70,    'amount_currency': -50, 'currency_id': self.currency_usd_id},
            {'debit': 32.70,    'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_usd_id},
        ])
        self.assertRecordValues(supplier_move_lines, [
            {'debit': 32.70,    'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_usd_id},
            {'debit': 0.0,      'credit': 32.70,    'amount_currency': -50, 'currency_id': self.currency_usd_id},
        ])

    def test_statement_usd_invoice_usd_transaction_eur(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_usd, 50, 40, self.currency_euro_id)
        self.assertRecordValues(customer_move_lines, [
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -50, 'currency_id': self.currency_usd_id},
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_usd_id},
        ])
        exchange_lines = customer_move_lines.mapped('full_reconcile_id.exchange_move_id.line_ids')
        self.assertRecordValues(exchange_lines, [
             {'debit': 7.30,    'credit': 0.0,      'account_id': self.account_rcv.id},
             {'debit': 0.0,     'credit': 7.30,     'account_id': self.diff_income_account.id},
        ])

        self.assertRecordValues(supplier_move_lines, [
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_usd_id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -50, 'currency_id': self.currency_usd_id},
        ])
        exchange_lines = supplier_move_lines.mapped('full_reconcile_id.exchange_move_id.line_ids')
        self.assertRecordValues(exchange_lines, [
             {'debit': 0.0,     'credit': 7.30,     'account_id': self.account_rsa.id},
             {'debit': 7.30,    'credit': 0.0,      'account_id': self.diff_expense_account.id},
        ])

    def test_statement_usd_invoice_chf_transaction_chf(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_swiss_id, 50, self.bank_journal_usd, 42, 50, self.currency_swiss_id)
        self.assertRecordValues(customer_move_lines, [
            {'debit': 0.0,      'credit': 27.47,    'amount_currency': -50, 'currency_id': self.currency_swiss_id},
            {'debit': 27.47,    'credit': 0.0,      'amount_currency': 42,  'currency_id': self.currency_usd_id},
        ])
        exchange_lines = customer_move_lines.mapped('full_reconcile_id.exchange_move_id.line_ids')
        self.assertRecordValues(exchange_lines, [
            {'debit': 0.0,      'credit': 10.74,    'account_id': self.account_rcv.id},
            {'debit': 10.74,    'credit': 0.0,      'account_id': self.diff_expense_account.id},
        ])

        self.assertRecordValues(supplier_move_lines, [
            {'debit': 27.47,    'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_swiss_id},
            {'debit': 0.0,      'credit': 27.47,    'amount_currency': -42, 'currency_id': self.currency_usd_id},
        ])
        exchange_lines = supplier_move_lines.mapped('full_reconcile_id.exchange_move_id.line_ids')
        self.assertRecordValues(exchange_lines, [
            {'debit': 10.74,    'credit': 0.0,      'account_id': self.account_rsa.id},
            {'debit': 0.0,      'credit': 10.74,    'account_id': self.diff_income_account.id},
        ])

    def test_statement_eur_invoice_usd_transaction_usd(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_euro, 40, 50, self.currency_usd_id)
        self.assertRecordValues(customer_move_lines, [
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -50, 'currency_id': self.currency_usd_id},
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_usd_id},
        ])
        exchange_lines = customer_move_lines.mapped('full_reconcile_id.exchange_move_id.line_ids')
        self.assertRecordValues(exchange_lines, [
            {'debit': 7.30,     'credit': 0.0,      'account_id': self.account_rcv.id},
            {'debit': 0.0,      'credit': 7.30,     'account_id': self.diff_income_account.id},
        ])

        self.assertRecordValues(supplier_move_lines, [
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_usd_id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -50, 'currency_id': self.currency_usd_id},
        ])
        exchange_lines = supplier_move_lines.mapped('full_reconcile_id.exchange_move_id.line_ids')
        self.assertRecordValues(exchange_lines, [
            {'debit': 0.0,      'credit': 7.30,     'account_id': self.account_rsa.id},
            {'debit': 7.30,     'credit': 0.0,      'account_id': self.diff_expense_account.id},
        ])

    def test_statement_eur_invoice_usd_transaction_eur(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_euro, 40, 0.0, False)
        self.assertRecordValues(customer_move_lines, [
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': 0.0, 'currency_id': False},
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 0.0, 'currency_id': False},
        ])
        self.assertRecordValues(supplier_move_lines, [
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 0.0, 'currency_id': False},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': 0.0, 'currency_id': False},
        ])

    def test_statement_euro_invoice_usd_transaction_chf(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_euro, 42, 50, self.currency_swiss_id)
        self.assertRecordValues(customer_move_lines, [
            {'debit': 0.0,      'credit': 42.0,     'amount_currency': -50, 'currency_id': self.currency_swiss_id},
            {'debit': 42.0,     'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_swiss_id},
        ])
        self.assertRecordValues(supplier_move_lines, [
            {'debit': 42.0,     'credit': 0.0,      'amount_currency': 50,  'currency_id': self.currency_swiss_id},
            {'debit': 0.0,      'credit': 42.0,     'amount_currency': -50, 'currency_id': self.currency_swiss_id},
        ])

    def test_statement_euro_invoice_usd_transaction_euro_full(self):
        # Create a customer invoice of 50 USD.
        partner = self.env['res.partner'].create({'name': 'test'})
        move = self.env['account.move'].with_context(default_type='out_invoice').create({
            'type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': '%s-07-01' % time.strftime('%Y'),
            'date': '%s-07-01' % time.strftime('%Y'),
            'currency_id': self.currency_usd_id,
            'invoice_line_ids': [
                (0, 0, {'quantity': 1, 'price_unit': 50.0, 'name': 'test'})
            ],
        })
        move.post()

        # Create a bank statement of 40 EURO.
        bank_stmt = self.env['account.bank.statement'].create({
            'journal_id': self.bank_journal_euro.id,
            'date': '%s-01-01' % time.strftime('%Y'),
            'line_ids': [
                (0, 0, {
                    'name': 'test',
                    'partner_id': partner.id,
                    'amount': 40.0,
                    'date': '%s-01-01' % time.strftime('%Y')
                })
            ],
        })

        # Reconcile the bank statement with the invoice.
        receivable_line = move.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        bank_stmt.line_ids[0].process_reconciliation(counterpart_aml_dicts=[{
              'move_line': receivable_line,
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
            {'debit': 0.0,      'credit': 7.3,      'amount_currency': 0.0,     'currency_id': False},
            {'debit': 0.0,      'credit': 32.7,     'amount_currency': 0.0,     'currency_id': False},
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 0.0,     'currency_id': False},
        ])

        # The invoice should be paid, as the payments totally cover its total
        self.assertEquals(move.invoice_payment_state, 'paid', 'The invoice should be paid by now')
        self.assertTrue(receivable_line.reconciled, 'The invoice should be totally reconciled')
        self.assertTrue(receivable_line.full_reconcile_id, 'The invoice should have a full reconcile number')
        self.assertEquals(receivable_line.amount_residual, 0, 'The invoice should be totally reconciled')
        self.assertEquals(receivable_line.amount_residual_currency, 0, 'The invoice should be totally reconciled')

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
            'invoice_date': time.strftime('%Y-%m-%d'),
            'date': time.strftime('%Y-%m-%d'),
            'journal_id': self.bank_journal_usd_id,
            'invoice_line': [
                (0, 0, {
                    'name': 'line that will lead to an exchange gain',
                    'quantity': 1,
                    'price_unit': 2,
                })
            ]
        })
        invoice.post()
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
        for l in invoice.line_id:
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
            reconcile = payment.reconcile_model_id
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
            'invoice_ids': [(6, 0, invoice.ids)],
            })
        payment.post()
        bank_move_line = payment.move_line_ids.filtered(lambda line: line.account_id.internal_type == 'liquidity')

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
        dest_journal_id.write({'default_debit_account_id': self.bank_journal_euro.default_credit_account_id,
                               'default_credit_account_id': self.bank_journal_euro.default_credit_account_id})
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
        invoice_a = self.env['account.move'].with_context(default_type='in_invoice').create({
            'type': 'in_invoice',
            'partner_id': self.partner_agrolait_id,
            'currency_id': self.currency_usd_id,
            'invoice_date': '%s-07-01' % time.strftime('%Y'),
            'date': '%s-07-01' % time.strftime('%Y'),
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product.id, 'quantity': 1, 'price_unit': 50.0})
            ],
        })
        invoice_b = self.env['account.move'].with_context(default_type='in_invoice').create({
            'type': 'in_invoice',
            'partner_id': self.partner_agrolait_id,
            'currency_id': self.currency_usd_id,
            'invoice_date': '%s-08-01' % time.strftime('%Y'),
            'date': '%s-08-01' % time.strftime('%Y'),
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product.id, 'quantity': 1, 'price_unit': 50.0})
            ],
        })
        (invoice_a + invoice_b).post()

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
        debit_line_a = payment_a.move_line_ids.filtered(lambda l: l.debit and l.account_id == self.account_rsa)
        debit_line_b = payment_b.move_line_ids.filtered(lambda l: l.debit and l.account_id == self.account_rsa)
        debit_line_c = payment_c.move_line_ids.filtered(lambda l: l.debit and l.account_id == self.account_rsa)

        invoice_a.js_assign_outstanding_line(debit_line_a.id)
        invoice_a.js_assign_outstanding_line(debit_line_b.id)
        invoice_b.js_assign_outstanding_line(debit_line_b.id)
        invoice_b.js_assign_outstanding_line(debit_line_c.id)

        # Asserting correctness (only in the payable account)
        full_reconcile = False
        reconciled_amls = (debit_line_a + debit_line_b + debit_line_c + (invoice_a + invoice_b).mapped('line_ids'))\
            .filtered(lambda l: l.account_id == self.account_rsa)
        for aml in reconciled_amls:
            self.assertEqual(aml.amount_residual, 0.0)
            self.assertEqual(aml.amount_residual_currency, 0.0)
            self.assertTrue(aml.reconciled)
            if not full_reconcile:
                full_reconcile = aml.full_reconcile_id
            else:
                self.assertTrue(aml.full_reconcile_id == full_reconcile)

        full_rec_move = full_reconcile.exchange_move_id
        # Globally check whether the amount is correct
        self.assertEqual(sum(full_rec_move.mapped('line_ids.debit')), 18.75)

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
        self.assertAlmostEquals(inv1.amount_residual, 10)
        self.assertAlmostEquals(inv2.amount_residual, 20)

        # Assign credit and residual
        inv1.js_assign_outstanding_line(credit_aml.id)
        inv2.js_assign_outstanding_line(credit_aml.id)
        self.assertAlmostEquals(inv1.amount_residual, 0)
        self.assertAlmostEquals(inv2.amount_residual, 0)

        # Unreconcile one invoice at a time and check residual
        credit_aml.remove_move_reconcile()
        self.assertAlmostEquals(inv1.amount_residual, 10)
        self.assertAlmostEquals(inv2.amount_residual, 20)

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
        self.assertAlmostEquals(inv.amount_residual, 111)

        # Assign credit, check exchange move and residual
        inv.js_assign_outstanding_line(credit_aml.id)
        self.assertEqual(len(payment.move_line_ids.mapped('full_reconcile_id').exchange_move_id), 1)
        self.assertAlmostEquals(inv.amount_residual, 0)

        # Unreconcile invoice and check residual
        credit_aml.with_context(invoice_id=inv.id).remove_move_reconcile()
        self.assertAlmostEquals(inv.amount_residual, 111)

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
        reversed_move = move._reverse_moves([{'date': '2018-06-04'}])
        self.assertEqual(len(reversed_move), 1)

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


    def test_aged_report(self):
        AgedReport = self.env['report.account.report_agedpartnerbalance'].with_context(include_nullified_amount=True)
        account_type = ['receivable']
        report_date_to = time.strftime('%Y') + '-07-17'
        partner = self.env['res.partner'].create({'name': 'AgedPartner'})
        currency = self.env.company.currency_id

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
        invoice.line_ids.with_context(invoice_id=invoice.id).remove_move_reconcile()
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
        inv.js_assign_outstanding_line(credit_aml.id)
        self.assertTrue(inv.invoice_payment_state == 'paid', 'The invoice should be paid')

        exchange_reconcile = payment.move_line_ids.mapped('full_reconcile_id')
        exchange_move = exchange_reconcile.exchange_move_id
        payment_move = payment.move_line_ids[0].move_id

        reverted_payment_move = payment_move._reverse_moves([{'date': time.strftime('%Y') + '-08-01'}], cancel=True)

        # After reversal of payment, the invoice should be open
        self.assertTrue(inv.state == 'posted', 'The invoice should be open again')
        self.assertFalse(exchange_reconcile.exists())

        reverted_exchange_move = self.env['account.move'].search([('journal_id', '=', exchange_move.journal_id.id), ('ref', 'ilike', exchange_move.name)], limit=1)
        _move_revert_test_pair(payment_move, reverted_payment_move)
        _move_revert_test_pair(exchange_move, reverted_exchange_move)

    def test_aged_report_future_payment(self):
        AgedReport = self.env['report.account.report_agedpartnerbalance'].with_context(include_nullified_amount=True)
        account_type = ['receivable']
        partner = self.env['res.partner'].create({'name': 'AgedPartner'})
        currency = self.env.company.currency_id

        invoice = self.create_invoice_partner(currency_id=currency.id, partner_id=partner.id)
        journal = self.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'THE'})

        statement = self.make_payment(invoice, journal, 50)

        # Force the payment recording to take place on the invoice date
        # Although the payment due_date is in the future relative to the invoice
        # Also, in this case, there can be only 1 partial_reconcile
        statement_partial_id = statement.move_line_ids.mapped(lambda l: l.matched_credit_ids + l.matched_debit_ids)
        self.env.cr.execute('UPDATE account_partial_reconcile SET create_date = %(date)s WHERE id = %(partial_id)s',
            {'date': invoice.invoice_date,
             'partial_id': statement_partial_id.id})
        statement.flush()

        # Case 1: report date is invoice date
        # There should be an entry for the partner
        report_date_to = invoice.invoice_date
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

        invoice_cust_1 = self.env['account.move'].with_context(default_type='out_invoice').create({
            'type': 'out_invoice',
            'partner_id': self.partner_agrolait_id,
            'invoice_date': '%s-01-01' % time.strftime('%Y'),
            'date': '%s-01-01' % time.strftime('%Y'),
            'currency_id': self.currency_usd_id,
            'invoice_line_ids': [
                (0, 0, {'quantity': 1, 'price_unit': 100.0, 'name': 'product that cost 100'})
            ],
        })
        invoice_cust_1.post()
        aml = invoice_cust_1.invoice_line_ids[0]
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
             'invoice_ids': [(6, 0, invoice_cust_1.ids)],
             })
        payment.post()
        # We expect at this point that the invoice should still be open,
        # because they owe us still 50 CC.
        self.assertEqual(invoice_cust_1.invoice_payment_state, 'not_paid', 'Invoice is in status %s' % invoice_cust_1.state)

    def test_inv_refund_foreign_payment_writeoff_domestic(self):
        company = self.env.ref('base.main_company')
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.113900,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id
        })
        inv1 = self.create_invoice(invoice_amount=480, currency_id=self.currency_usd_id)
        inv2 = self.create_invoice(type="out_refund", invoice_amount=140, currency_id=self.currency_usd_id)

        payment = self.env['account.payment'].create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_method_id': self.inbound_payment_method.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': inv1.partner_id.id,
            'amount': 287.20,
            'journal_id': self.bank_journal_euro.id,
            'company_id': company.id,
        })
        payment.post()

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        inv2_receivable = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        pay_receivable = payment.move_line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        data_for_reconciliation = [
            {
                'type': 'partner',
                'id': inv1.partner_id.id,
                'mv_line_ids': (inv1_receivable + inv2_receivable + pay_receivable).ids,
                'new_mv_line_dicts': [
                    {
                        'credit': 18.04,
                        'debit': 0.00,
                        'journal_id': self.bank_journal_euro.id,
                        'name': 'Total WriteOff (Fees)',
                        'account_id': self.diff_expense_account.id
                    }
                ]
            }
        ]

        self.env["account.reconciliation.widget"].process_move_lines(data_for_reconciliation)

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEquals(inv1_receivable.full_reconcile_id, inv2_receivable.full_reconcile_id)
        self.assertEquals(inv1_receivable.full_reconcile_id, pay_receivable.full_reconcile_id)

        self.assertTrue(all(l.reconciled for l in inv1_receivable))
        self.assertTrue(all(l.reconciled for l in inv2_receivable))

        self.assertEquals(inv1.invoice_payment_state, 'paid')
        self.assertEquals(inv2.invoice_payment_state, 'paid')

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
        invoice = self.create_invoice_partner(
            partner_id=self.partner_agrolait_id,
            payment_term_id=payment_term.id,
            currency_id=self.currency_usd_id,
        )

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

        receivable_line = payment.move_line_ids.filtered('credit')
        invoice.js_assign_outstanding_line(receivable_line.id)

        self.assertTrue(receivable_line.matched_debit_ids)

    def test_reconciliation_cash_basis01(self):
        # Simulates an expense made up by 2 lines
        # one is subject to a cash basis tax
        # the other is not subject to tax

        company = self.env.ref('base.main_company')
        company.tax_cash_basis_journal_id = self.cash_basis_journal

        purchase_move = self.env['account.move'].create({
            'journal_id': self.purchase_journal.id,
            'line_ids': [
                (0, 0, {'account_id': self.account_rsa.id, 'debit': 0.0, 'credit': 100.0}),
                (0, 0, {'account_id': self.account_rsa.id, 'debit': 0.0, 'credit': 50.0}),
                (0, 0, {'account_id': self.expense_account.id, 'debit': 50.0, 'credit': 0.0}),
                (0, 0, {'account_id': self.expense_account.id, 'debit': 83.33, 'credit': 0.0, 'tax_ids': [(4, self.tax_cash_basis.id)], 'tax_exigible': False}),
                (0, 0, {
                    'account_id': self.tax_waiting_account.id,
                    'debit': 16.67,
                    'credit': 0.0,
                    'tax_repartition_line_id': self.tax_cash_basis.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                    'tax_base_amount': 83.33,
                    'tax_exigible': False
                }),
            ],
        })

        purchase_payable_line0 = purchase_move.line_ids.filtered(lambda x: x.account_id.internal_type == 'payable' and x.credit == 100)
        purchase_payable_line1 = purchase_move.line_ids.filtered(lambda x: x.account_id.internal_type == 'payable' and x.credit == 50)
        tax_line = purchase_move.line_ids.filtered(lambda x: x.tax_line_id == self.tax_cash_basis)

        purchase_move.post()

        payment_move = self.env['account.move'].create({
            'journal_id': self.bank_journal_euro.id,
            'line_ids': [
                (0, 0, {'account_id': self.account_rsa.id, 'debit': 150.0, 'credit': 0.0}),
                (0, 0, {'account_id': self.account_euro.id, 'debit': 0.0, 'credit': 150.0}),
            ],
        })
        payment_move.post()

        (purchase_move + payment_move).invalidate_cache(['line_ids'])
        to_reconcile = (purchase_move + payment_move).mapped('line_ids').filtered(lambda l: l.account_id.internal_type == 'payable')
        to_reconcile.reconcile()

        cash_basis_moves = self.env['account.move'].search([('journal_id', '=', self.cash_basis_journal.id)])

        self.assertEqual(len(cash_basis_moves), 2)
        self.assertTrue(cash_basis_moves.exists())

        # check reconciliation in Payable account
        purchase_move_line_ids = purchase_move.line_ids.sorted()
        payment_move_line_ids = payment_move.line_ids.sorted()
        self.assertTrue(purchase_move_line_ids[0].full_reconcile_id.exists())
        self.assertEqual(purchase_move_line_ids[0].full_reconcile_id.reconciled_line_ids,
             purchase_move_line_ids[0] + purchase_move_line_ids[1] + payment_move_line_ids[0])

        cash_basis_aml_ids = cash_basis_moves.mapped('line_ids')
        # check reconciliation in the tax waiting account
        self.assertTrue(purchase_move_line_ids[4].full_reconcile_id.exists())
        self.assertEqual(purchase_move_line_ids[4].full_reconcile_id.reconciled_line_ids,
            cash_basis_aml_ids.filtered(lambda l: l.account_id == self.tax_waiting_account) + purchase_move_line_ids[4])

        self.assertEqual(len(cash_basis_aml_ids), 8)

        # check amounts
        cash_basis_move1 = cash_basis_moves.filtered(lambda m: m.amount_total == 33.34)
        cash_basis_move2 = cash_basis_moves.filtered(lambda m: m.amount_total == 66.66)

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

        purchase_move = self.env['account.move'].create({
            'journal_id': self.purchase_journal.id,
            'line_ids': [
                (0, 0, {'account_id': self.account_rsa.id, 'debit': 0.0, 'credit': 50.0}),
                (0, 0, {'account_id': self.account_rsa.id, 'debit': 0.0, 'credit': 105.0}),
                (0, 0, {'name': 'expenseTaxed 10%', 'account_id': self.expense_account.id, 'debit': 50.0, 'credit': 0.0, 'tax_ids': [(4, tax_cash_basis10percent.id)], 'tax_exigible': False}),
                (0, 0, {
                    'name': 'TaxLine0',
                    'account_id': tax_waiting_account10.id,
                    'debit': 5.0,
                    'credit': 0.0,
                    'tax_repartition_line_id': tax_cash_basis10percent.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                    'tax_exigible': False,
                    'tax_base_amount': 50.00,
                }),
                (0, 0, {'name': 'expenseTaxed 20%', 'account_id': self.expense_account.id, 'debit': 83.33, 'credit': 0.0, 'tax_ids': [(4, self.tax_cash_basis.id)], 'tax_exigible': False}),
                (0, 0, {
                    'name': 'TaxLine1',
                    'account_id': self.tax_waiting_account.id,
                    'debit': 16.67,
                    'credit': 0.0,
                    'tax_repartition_line_id': self.tax_cash_basis.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                    'tax_exigible': False,
                    'tax_base_amount': 83.33,
             }),
            ],
        })

        purchase_payable_line0 = purchase_move.line_ids.filtered(lambda x: x.account_id == self.account_rsa and x.credit == 105)
        purchase_payable_line1 = purchase_move.line_ids.filtered(lambda x: x.account_id == self.account_rsa and x.credit == 50)
        tax_line0 = purchase_move.line_ids.filtered(lambda x: x.tax_line_id == tax_cash_basis10percent)
        tax_line1 = purchase_move.line_ids.filtered(lambda x: x.tax_line_id == self.tax_cash_basis)

        purchase_move.post()

        payment_move0 = self.env['account.move'].create({
            'journal_id': self.bank_journal_euro.id,
            'line_ids': [
                (0, 0, {'account_id': self.account_rsa.id, 'debit': 40.0, 'credit': 0.0}),
                (0, 0, {'account_id': self.account_euro.id, 'debit': 0.0, 'credit': 40.0}),
            ],
        })
        payment_move0.post()

        payment_move1 = self.env['account.move'].create({
            'journal_id': self.bank_journal_euro.id,
            'line_ids': [
                (0, 0, {'account_id': self.account_rsa.id, 'debit': 115.0, 'credit': 0.0}),
                (0, 0, {'account_id': self.account_euro.id, 'debit': 0.0, 'credit': 115.0}),
            ],
        })
        payment_move1.post()

        (purchase_move + payment_move0).mapped('line_ids').sorted().filtered(lambda l: l.account_id.internal_type == 'payable').reconcile()
        (purchase_move + payment_move1).mapped('line_ids').sorted().filtered(lambda l: l.account_id.internal_type == 'payable').reconcile()

        cash_basis_moves = self.env['account.move'].search([('journal_id', '=', self.cash_basis_journal.id)])

        self.assertEqual(len(cash_basis_moves), 3)
        self.assertTrue(cash_basis_moves.exists())

        # check reconciliation in Payable account
        purchase_move_line_ids = purchase_move.line_ids.sorted()
        self.assertTrue(purchase_move_line_ids[0].full_reconcile_id.exists())
        self.assertEqual(purchase_move_line_ids[0].full_reconcile_id.reconciled_line_ids,
            (purchase_move + payment_move0 + payment_move1).mapped('line_ids').filtered(lambda l: l.account_id.internal_type == 'payable'))

        cash_basis_aml_ids = cash_basis_moves.mapped('line_ids')

        # check reconciliation in the tax waiting account
        self.assertTrue(purchase_move_line_ids[3].full_reconcile_id.exists())
        self.assertEqual(purchase_move_line_ids[3].full_reconcile_id.reconciled_line_ids,
            cash_basis_aml_ids.filtered(lambda l: l.account_id == tax_waiting_account10) + purchase_move_line_ids[3])

        self.assertTrue(purchase_move_line_ids[5].full_reconcile_id.exists())
        self.assertEqual(purchase_move_line_ids[5].full_reconcile_id.reconciled_line_ids,
            cash_basis_aml_ids.filtered(lambda l: l.account_id == self.tax_waiting_account) + purchase_move_line_ids[5])

        self.assertEqual(len(cash_basis_aml_ids), 24)

        # check amounts
        expected_move_amounts = [
            {'base_20': 56.45, 'tax_20': 11.29, 'base_10': 33.87, 'tax_10': 3.39},
            {'base_20': 5.38, 'tax_20': 1.08, 'base_10': 3.23, 'tax_10': 0.32},
            {'base_20': 21.50, 'tax_20': 4.30, 'base_10': 12.90, 'tax_10': 1.29},
        ]

        index = 0
        for cb_move in cash_basis_moves:
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

    def test_reconciliation_to_check(self):
        partner = self.env['res.partner'].create({'name': 'UncertainPartner'})
        currency = self.env.company.currency_id
        invoice = self.create_invoice_partner(currency_id=currency.id, partner_id=partner.id)
        journal = self.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'THE', 'restrict_mode_hash_table':False})

        statement = self.make_payment(invoice, journal, 50)
        st_line = statement.line_ids
        previous_move_lines = st_line.journal_entry_ids.ids
        previous_name = st_line.move_name

        with self.assertRaises(UserError): #you need edition mode to be able to change it
            st_line.with_context(suspense_moves_mode=False).process_reconciliation(
                counterpart_aml_dicts=[],
                new_aml_dicts=[{
                  'debit': 0,
                  'credit': 50,
                  'name': 'exchange difference',
                  'account_id': self.diff_income_account.id
                }],
            )

        st_line.with_context(suspense_moves_mode=True).process_reconciliation(
            counterpart_aml_dicts=[],
            new_aml_dicts=[{
              'debit': 0,
              'credit': 50,
              'name': 'exchange difference',
              'account_id': self.diff_income_account.id
            }],
        )
        self.assertEqual(previous_name, st_line.move_name) # the name of the move hasnt changed
        self.assertNotEqual(previous_move_lines, st_line.journal_entry_ids.ids) # the lines are new

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

        # Purchase
        purchase_move = self.env['account.move'].create({
            'journal_id': self.purchase_journal.id,
            'line_ids': [
                (0, 0, {
                    'name': 'expenseTaxed',
                    'account_id': self.expense_account.id,
                    'currency_id': self.currency_usd_id,
                    'tax_ids': [(4, self.tax_cash_basis.id)],
                    'tax_exigible': False,
                    'debit': 106841.65, 'credit': 0.0, 'amount_currency': 5301.00,
                }),
                (0, 0, {
                    'name': 'TaxLine',
                    'account_id': self.tax_waiting_account.id,
                    'currency_id': self.currency_usd_id,
                    'tax_repartition_line_id': self.tax_cash_basis.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                    'tax_exigible': False,
                    'tax_base_amount': 106841.65,
                    'debit': 17094.66, 'credit': 0.0, 'amount_currency': 848.16,
                }),
                (0, 0, {
                    'name': 'Payable',
                    'account_id': self.account_rsa.id,
                    'currency_id': self.currency_usd_id,
                    'debit': 0.0, 'credit': 123936.31, 'amount_currency': -6149.16,
                }),
            ],
        })

        purchase_payable_line0 = purchase_move.line_ids.filtered(lambda x: x.account_id.internal_type == 'payable')

        purchase_move.post()

        # FX 01 Move
        fx_move_01 = self.env['account.move'].create({
            'journal_id': self.fx_journal.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.account_rsa.id,
                    'currency_id': self.currency_usd_id,
                    'debit': 167.86, 'credit': 0.0, 'amount_currency': 0.00,
                }),
                (0, 0, {
                    'account_id': self.diff_income_account.id,
                    'currency_id': self.currency_usd_id,
                    'debit': 0.0, 'credit': 167.86, 'amount_currency': 0.0,
                }),
            ],
        })
        fx_move_01.post()

        # Payment Move
        payment_move = self.env['account.move'].create({
            'journal_id': self.bank_journal_usd.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.account_rsa.id,
                    'currency_id': self.currency_usd_id,
                    'debit': 123768.45, 'credit': 0.0, 'amount_currency': 6149.16,
                }),
                (0, 0, {
                    'account_id': self.account_usd.id,
                    'currency_id': self.currency_usd_id,
                    'debit': 0.0, 'credit': 123768.45, 'amount_currency': -6149.16,
                }),
            ],
        })
        payment_move.post()

        to_reconcile = (
            (purchase_move + payment_move + fx_move_01).mapped('line_ids')
            .filtered(lambda l: l.account_id.internal_type == 'payable'))
        to_reconcile.reconcile()

        # check reconciliation in Payable account
        purchase_line_ids = purchase_move.line_ids.sorted()
        fx_move_01_line_ids = fx_move_01.line_ids.sorted()
        payment_move_line_ids = payment_move.line_ids.sorted()
        self.assertTrue(purchase_line_ids[2].full_reconcile_id.exists())
        self.assertEqual(
            purchase_line_ids[2].full_reconcile_id.reconciled_line_ids,
            purchase_line_ids[2] + fx_move_01_line_ids[0] + payment_move_line_ids[0])

        # check cash basis
        cash_basis_moves = self.env['account.move'].search(
            [('journal_id', '=', self.cash_basis_journal.id)])

        self.assertEqual(len(cash_basis_moves), 1)

        cash_basis_aml_ids = cash_basis_moves.mapped('line_ids')
        self.assertEqual(len(cash_basis_aml_ids), 4)

        # check amounts
        cash_basis_move1 = cash_basis_moves.filtered(lambda m: m.currency_id.is_zero(sum(line.credit for line in m.line_ids) - 123936.31))

        self.assertTrue(cash_basis_move1.exists())

        # For first move
        move_lines = cash_basis_moves.line_ids
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

        # Purchase
        purchase_move = self.env['account.move'].create({
            'journal_id': self.purchase_journal.id,
            'line_ids': [
                (0, 0, {
                    'name': 'expenseTaxed',
                    'account_id': self.expense_account.id,
                    'currency_id': self.currency_usd_id,
                    'tax_ids': [(4, self.tax_cash_basis.id)],
                    'tax_exigible': False,
                    'debit': 106841.65, 'credit': 0.0, 'amount_currency': 5301.00,
                }),
                (0, 0, {
                    'name': 'TaxLine',
                    'account_id': self.tax_waiting_account.id,
                    'currency_id': self.currency_usd_id,
                    'tax_repartition_line_id': self.tax_cash_basis.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                    'tax_exigible': False,
                    'tax_base_amount': 106841.65,
                    'debit': 17094.66, 'credit': 0.0, 'amount_currency': 848.16,
                }),
                (0, 0, {
                    'name': 'Payable',
                    'account_id': self.account_rsa.id,
                    'currency_id': self.currency_usd_id,
                    'debit': 0.0, 'credit': 123936.31, 'amount_currency': -6149.16,
                }),
            ],
        })

        purchase_payable_line0 = purchase_move.line_ids.filtered(lambda x: x.account_id.internal_type == 'payable')

        purchase_move.post()

        # FX 01 Move
        fx_move_01 = self.env['account.move'].create({
            'journal_id': self.fx_journal.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.account_rsa.id,
                    'currency_id': self.currency_usd_id,
                    'debit': 0.0, 'credit': 1572.96, 'amount_currency': 0.00,
                }),
                (0, 0, {
                    'account_id': self.diff_expense_account.id,
                    'currency_id': self.currency_usd_id,
                    'debit': 1572.96, 'credit': 0.0, 'amount_currency': 0.0,
                }),
            ],
        })
        fx_move_01.post()

        # FX 02 Move
        fx_move_02 = self.env['account.move'].create({
            'journal_id': self.fx_journal.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.account_rsa.id,
                    'currency_id': self.currency_usd_id,
                    'debit': 1740.82, 'credit': 0.0, 'amount_currency': 0.00,
                }),
                (0, 0, {
                    'account_id': self.diff_income_account.id,
                    'currency_id': self.currency_usd_id,
                    'debit': 0.0, 'credit': 1740.82, 'amount_currency': 0.0,
                }),
            ],
        })
        fx_move_02.post()

        # Payment Move
        payment_move = self.env['account.move'].create({
            'journal_id': self.bank_journal_usd.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.account_rsa.id,
                    'currency_id': self.currency_usd_id,
                    'debit': 123768.45, 'credit': 0.0, 'amount_currency': 6149.16,
                }),
                (0, 0, {
                    'account_id': self.account_usd.id,
                    'currency_id': self.currency_usd_id,
                    'debit': 0.0, 'credit': 123768.45, 'amount_currency': -6149.16,
                }),
            ],
        })
        payment_move.post()

        to_reconcile = (
            (purchase_move + payment_move + fx_move_01 + fx_move_02)
            .mapped('line_ids')
            .filtered(lambda l: l.account_id.internal_type == 'payable'))
        to_reconcile.reconcile()

        # check reconciliation in Payable account
        purchase_move_line_ids = purchase_move.line_ids.sorted()
        fx_move_01_line_ids = fx_move_01.line_ids.sorted()
        fx_move_02_line_ids = fx_move_02.line_ids.sorted()
        payment_move_line_ids = payment_move.line_ids.sorted()
        self.assertTrue(purchase_move_line_ids[2].full_reconcile_id.exists())
        self.assertEqual(
            purchase_move_line_ids[2].full_reconcile_id.reconciled_line_ids,
            purchase_move_line_ids[2] + fx_move_01_line_ids[0] + fx_move_02_line_ids[0] +
            payment_move_line_ids[0])

        # check cash basis
        cash_basis_moves = self.env['account.move'].search(
            [('journal_id', '=', self.cash_basis_journal.id)])

        self.assertEqual(len(cash_basis_moves), 1)

        cash_basis_aml_ids = cash_basis_moves.mapped('line_ids')
        self.assertEqual(len(cash_basis_aml_ids), 4)

        # check amounts
        cash_basis_move1 = cash_basis_moves.filtered(lambda m: m.currency_id.is_zero(sum(line.credit for line in m.line_ids) - 123936.31))

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

        # Purchase
        purchase_move = self.env['account.move'].create({
            'name': 'invoice',
            'journal_id': self.purchase_journal.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.account_rsa.id,
                    'credit': 175,
                }),

                (0, 0, {
                    'name': 'expenseTaxed 10%',
                    'account_id': self.expense_account.id,
                    'debit': 50,
                    'tax_ids': [(4, tax_cash_basis10percent.id, False)],
                }),

                (0, 0, {
                    'name': 'TaxLine0',
                    'account_id': tax_waiting_account10.id,
                    'debit': 5,
                    'tax_repartition_line_id': tax_cash_basis10percent.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                    'tax_base_amount': 50,
                }),

                (0, 0, {
                    'name': 'expenseTaxed 20%',
                    'account_id': self.expense_account.id,
                    'debit': 100,
                    'tax_ids': [(4, self.tax_cash_basis.id, False)],
                }),

                (0, 0, {
                    'name': 'TaxLine1',
                    'account_id': self.tax_waiting_account.id,
                    'debit': 20,
                    'tax_repartition_line_id': self.tax_cash_basis.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                    'tax_base_amount': 100,
                }),
            ],
        })

        purchase_payable_line0 = purchase_move.line_ids.filtered(lambda x: x.account_id.internal_type == 'payable')
        tax_line0 = purchase_move.line_ids.filtered(lambda x: x.tax_line_id == tax_cash_basis10percent)
        tax_line1 = purchase_move.line_ids.filtered(lambda x: x.tax_line_id == self.tax_cash_basis)

        purchase_move.post()

        reverted = purchase_move._reverse_moves(cancel=True)
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

        move_form = Form(self.env['account.move'].with_context(default_type='out_invoice'))
        move_form.partner_id = self.partner_agrolait
        move_form.currency_id = self.env.ref('base.USD')
        move_form.invoice_date = time.strftime('%Y') + '-07-01'
        with move_form.invoice_line_ids.new() as line_form:
            line_form.name = 'test line'
            line_form.price_unit = 50
            line_form.tax_ids.clear()
        invoice = move_form.save()
        move_form = Form(invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.tax_ids.add(self.tax_cash_basis)
        invoice = move_form.save()
        invoice.post()

        self.assertTrue(invoice.currency_id != self.env.user.company_id.currency_id)

        # First Payment
        payment0 = self.make_payment(invoice, journal, amount=59.99)
        self.assertEqual(invoice.amount_residual, 0.01)

        tax_waiting_line = invoice.line_ids.filtered(lambda l: l.account_id == self.tax_waiting_account)
        self.assertTrue(tax_waiting_line.exists())
        self.assertFalse(tax_waiting_line.reconciled)

        move_caba0 = tax_waiting_line.matched_debit_ids.debit_move_id.move_id
        self.assertTrue(move_caba0.exists())
        self.assertEqual(move_caba0.journal_id, self.env.user.company_id.tax_cash_basis_journal_id)

        pay_receivable_line0 = payment0.move_line_ids.filtered(lambda l: l.account_id == self.account_rcv)
        self.assertTrue(pay_receivable_line0.reconciled)
        self.assertEqual(pay_receivable_line0.matched_debit_ids, move_caba0.tax_cash_basis_rec_id)

        # Second Payment
        payment1 = self.make_payment(invoice, journal, 0.01)
        self.assertEqual(invoice.amount_residual, 0)
        self.assertEqual(invoice.invoice_payment_state, 'paid')

        self.assertTrue(tax_waiting_line.reconciled)
        move_caba1 = tax_waiting_line.matched_debit_ids.mapped('debit_move_id').mapped('move_id').filtered(lambda m: m != move_caba0)
        self.assertEqual(len(move_caba1.exists()), 1)
        self.assertEqual(move_caba1.journal_id, self.env.user.company_id.tax_cash_basis_journal_id)

        pay_receivable_line1 = payment1.move_line_ids.filtered(lambda l: l.account_id == self.account_rcv)
        self.assertTrue(pay_receivable_line1.reconciled)
        self.assertEqual(pay_receivable_line1.matched_debit_ids, move_caba1.tax_cash_basis_rec_id)

    def test_caba_mix_reconciliation(self):
        """ Test the reconciliation of tax lines (when using a reconcilable tax account)
        for cases mixing taxes exigible on payment and on invoices.
        This test is especially useful to check the implementation of the use case tested by
        test_reconciliation_cash_basis_foreign_currency_low_values does not have unwanted side effects.
        """

        # Make the tax account reconcilable
        self.tax_final_account.reconcile = True

        # Create a tax using the same accounts as the CABA one
        non_caba_tax = self.env['account.tax'].create({
            'name': 'tax 20%',
            'type_tax_use': 'purchase',
            'company_id': self.tax_cash_basis.company_id.id,
            'amount': 20,
            'tax_exigibility': 'on_invoice',
            'invoice_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),

                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': self.tax_final_account.id,
                }),
            ],
            'refund_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),

                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': self.tax_final_account.id,
                }),
            ],
        })

        # Create an invoice with a non-CABA tax
        non_caba_inv = self._create_invoice(type='in_invoice', invoice_amount=1000, tax=non_caba_tax, auto_validate=True)

        # Create an invoice with a CABA tax using the same tax account and pay it
        caba_inv = self._create_invoice(type='in_invoice', invoice_amount=500, tax=self.tax_cash_basis, auto_validate=True)

        pmt_wizard = self.env['account.payment.register'].with_context(active_model='account.invoice', active_ids=caba_inv.ids).create({
            'payment_date': caba_inv.date,
            'journal_id': self.bank_journal_euro.id,
            'payment_method_id': self.inbound_payment_method.id,
        })
        pmt_wizard.create_payments()

        partial_rec = caba_inv.mapped('line_ids.matched_debit_ids')
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', '=', partial_rec.id)])

        # Create a misc operation with a line on the tax account, for full reconcile of those tax lines
        misc_move = self.env['account.move'].create({
            'name': "Misc move",
            'journal_id': self.general_journal.id,
            'line_ids': [
                (0, 0, {
                    'name': 'line 1',
                    'account_id': self.tax_final_account.id,
                    'credit': 300,
                }),
                (0, 0, {
                    'name': 'line 2',
                    'account_id': self.expense_account.id, # Whatever the account here
                    'debit': 300,
                })
            ],
        })

        lines_to_reconcile = (misc_move + caba_move + non_caba_inv).mapped('line_ids').filtered(lambda x: x.account_id == self.tax_final_account)
        lines_to_reconcile.reconcile()

        # Check full reconciliation
        self.assertTrue(all(line.full_reconcile_id for line in lines_to_reconcile), "All tax lines should be fully reconciled")

    def test_reconciliation_cash_basis_tags(self):
        invoice = self._create_invoice(auto_validate=True, tax=self.tax_cash_basis)
        self.env['account.payment.register'].with_context(active_ids=invoice.ids).create({}).create_payments()
        partial_rec = invoice.line_ids.filtered(lambda x: x.account_id.user_type_id.type == 'receivable').matched_credit_ids
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', '=', partial_rec.id)])

        caba_base_line = caba_move.line_ids.filtered(lambda x: x.tax_ids)
        caba_tax_line = caba_move.line_ids.filtered(lambda x: x.tax_line_id)
        other_lines = caba_move.line_ids - (caba_base_line + caba_tax_line)

        self.assertRecordValues(caba_base_line + caba_tax_line, [
          {'tag_ids': self.tax_tag_base.ids},
          {'tag_ids': self.tax_tag_tax.ids},
        ])

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

    def test_reconciliation_process_move_lines_with_mixed_currencies(self):
        # Delete any old rate - to make sure that we use the ones we need.
        old_rates = self.env['res.currency.rate'].search(
            [('currency_id', '=', self.currency_usd_id)])
        old_rates.unlink()

        self.env['res.currency.rate'].create({
            'currency_id': self.currency_usd_id,
            'name': time.strftime('%Y') + '-01-01',
            'rate': 2,
        })

        move_product = self.env['account.move'].create({
            'ref': 'move product',
        })
        move_product_lines = self.env['account.move.line'].create([
            {
                'name': 'line product',
                'move_id': move_product.id,
                'account_id': self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1).id,
                'debit': 20,
                'credit': 0,
            },
            {
                'name': 'line receivable',
                'move_id': move_product.id,
                'account_id': self.account_rcv.id,
                'debit': 0,
                'credit': 20,
            }
        ])
        move_product.post()

        move_payment = self.env['account.move'].create({
            'ref': 'move payment',
        })
        liquidity_account = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_liquidity').id)], limit=1)
        move_payment_lines = self.env['account.move.line'].create([
            {
                'name': 'line product',
                'move_id': move_payment.id,
                'account_id': liquidity_account.id,
                'debit': 10.0,
                'credit': 0,
                'amount_currency': 20,
                'currency_id': self.currency_usd_id,
            },
            {
                'name': 'line product',
                'move_id': move_payment.id,
                'account_id': self.account_rcv.id,
                'debit': 0,
                'credit': 10.0,
                'amount_currency': -20,
                'currency_id': self.currency_usd_id,
            }
        ])
        move_product.post()

        # We are reconciling a move line in currency A with a move line in currency B and putting
        # the rest in a writeoff, this test ensure that the debit/credit value of the writeoff is
        # correctly computed in company currency.
        self.env['account.reconciliation.widget'].process_move_lines([{
            'id': False,
            'type': False,
            'mv_line_ids': [move_payment_lines[1].id, move_product_lines[1].id],
            'new_mv_line_dicts': [{
                'account_id': liquidity_account.id,
                'analytic_tag_ids': [(6, None, [])],
                'credit': 0,
                'date': time.strftime('%Y') + '-01-01',
                'debit': 15.0,
                'journal_id': self.env['account.journal'].search([('type', '=', 'sale')], limit=1).id,
                'name': 'writeoff',
            }],
        }])

        writeoff_line = self.env['account.move.line'].search([('name', '=', 'writeoff')])
        self.assertEquals(writeoff_line.credit, 15.0)

    def test_inv_refund_foreign_payment_writeoff_domestic2(self):
        company = self.env.ref('base.main_company')
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.110600,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id
        })
        inv1 = self.create_invoice(invoice_amount=800, currency_id=self.currency_usd_id)
        inv2 = self.create_invoice(type="out_refund", invoice_amount=400, currency_id=self.currency_usd_id)

        payment = self.env['account.payment'].create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_method_id': self.inbound_payment_method.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': inv1.partner_id.id,
            'amount': 200.00,
            'journal_id': self.bank_journal_euro.id,
            'company_id': company.id,
        })
        payment.post()

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        inv2_receivable = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        pay_receivable = payment.move_line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        move_balance = self.env['account.move'].create({
            'partner_id': inv1.partner_id.id,
            'date': time.strftime('%Y') + '-07-01',
            'journal_id': self.bank_journal_euro.id,
            'line_ids': [
                (0, False, {'credit': 160.16, 'account_id': inv1_receivable.account_id.id, 'name': 'Balance WriteOff'}),
                (0, False, {'debit': 160.16, 'account_id': self.diff_expense_account.id, 'name': 'Balance WriteOff'}),
            ]
        })

        move_balance.post()
        move_balance_receiv = move_balance.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        (inv1_receivable + inv2_receivable + pay_receivable + move_balance_receiv).reconcile()

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEquals(inv1_receivable.full_reconcile_id, inv2_receivable.full_reconcile_id)
        self.assertEquals(inv1_receivable.full_reconcile_id, pay_receivable.full_reconcile_id)
        self.assertEquals(inv1_receivable.full_reconcile_id, move_balance_receiv.full_reconcile_id)

        self.assertEquals(inv1.invoice_payment_state, 'paid')
        self.assertEquals(inv2.invoice_payment_state, 'paid')

    def test_inv_refund_foreign_payment_writeoff_domestic3(self):
        """
                    Receivable
                Domestic (Foreign)
        592.47 (658.00) |                    INV 1  > Done in foreign
                        |   202.59 (225.00)  INV 2  > Done in foreign
                        |   372.10 (413.25)  PAYMENT > Done in domestic (the 413.25 is virtual, non stored)
                        |    17.78  (19.75)  WriteOff > Done in domestic (the 19.75 is virtual, non stored)

        Reconciliation should be full
        Invoices should be marked as paid
        """
        company = self.env.ref('base.main_company')
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.110600,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id
        })
        inv1 = self.create_invoice(invoice_amount=658, currency_id=self.currency_usd_id)
        inv2 = self.create_invoice(type="out_refund", invoice_amount=225, currency_id=self.currency_usd_id)

        payment = self.env['account.payment'].create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_method_id': self.inbound_payment_method.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': inv1.partner_id.id,
            'amount': 372.10,
            'payment_date': time.strftime('%Y') + '-07-01',
            'journal_id': self.bank_journal_euro.id,
            'company_id': company.id,
        })
        payment.post()

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        inv2_receivable = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        pay_receivable = payment.move_line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        move_balance = self.env['account.move'].create({
            'partner_id': inv1.partner_id.id,
            'date': time.strftime('%Y') + '-07-01',
            'journal_id': self.bank_journal_euro.id,
            'line_ids': [
                (0, False, {'credit': 17.78, 'account_id': inv1_receivable.account_id.id, 'name': 'Balance WriteOff'}),
                (0, False, {'debit': 17.78, 'account_id': self.diff_expense_account.id, 'name': 'Balance WriteOff'}),
            ]
        })

        move_balance.post()
        move_balance_receiv = move_balance.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        (inv1_receivable + inv2_receivable + pay_receivable + move_balance_receiv).reconcile()

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEquals(inv1_receivable.full_reconcile_id, inv2_receivable.full_reconcile_id)
        self.assertEquals(inv1_receivable.full_reconcile_id, pay_receivable.full_reconcile_id)
        self.assertEquals(inv1_receivable.full_reconcile_id, move_balance_receiv.full_reconcile_id)

        self.assertFalse(inv1_receivable.full_reconcile_id.exchange_move_id)

        self.assertEquals(inv1.invoice_payment_state, 'paid')
        self.assertEquals(inv2.invoice_payment_state, 'paid')

    def test_inv_refund_foreign_payment_writeoff_domestic4(self):
        """
                    Receivable
                Domestic (Foreign)
        658.00 (658.00) |                    INV 1  > Done in foreign
                        |   202.59 (225.00)  INV 2  > Done in foreign
                        |   372.10 (413.25)  PAYMENT > Done in domestic (the 413.25 is virtual, non stored)
                        |    83.31  (92.52)  WriteOff > Done in domestic (the 92.52 is virtual, non stored)

        Reconciliation should be full
        Invoices should be marked as paid
        """
        company = self.env.ref('base.main_company')
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-15',
            'rate': 1.110600,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id
        })
        inv1 = self._create_invoice(invoice_amount=658, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-01', auto_validate=True)
        inv2 = self._create_invoice(type="out_refund", invoice_amount=225, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)

        payment = self.env['account.payment'].create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_method_id': self.inbound_payment_method.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': inv1.partner_id.id,
            'amount': 372.10,
            'journal_id': self.bank_journal_euro.id,
            'company_id': company.id,
            'currency_id': self.currency_euro_id,
        })
        payment.post()

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        inv2_receivable = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        pay_receivable = payment.move_line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertEqual(inv1_receivable.balance, 658)
        self.assertEqual(inv2_receivable.balance, -202.59)
        self.assertEqual(pay_receivable.balance, -372.1)

        move_balance = self.env['account.move'].create({
            'partner_id': inv1.partner_id.id,
            'date': time.strftime('%Y') + '-07-15',
            'journal_id': self.bank_journal_usd.id,
            'line_ids': [
                (0, False, {'credit': 83.31, 'account_id': inv1_receivable.account_id.id, 'name': 'Balance WriteOff'}),
                (0, False, {'debit': 83.31, 'account_id': self.diff_expense_account.id, 'name': 'Balance WriteOff'}),
            ]
        })

        move_balance.post()
        move_balance_receiv = move_balance.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        (inv1_receivable + inv2_receivable + pay_receivable + move_balance_receiv).reconcile()

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEquals(inv1_receivable.full_reconcile_id, inv2_receivable.full_reconcile_id)
        self.assertEquals(inv1_receivable.full_reconcile_id, pay_receivable.full_reconcile_id)
        self.assertEquals(inv1_receivable.full_reconcile_id, move_balance_receiv.full_reconcile_id)

        self.assertEquals(inv1.invoice_payment_state, 'paid')
        self.assertEquals(inv2.invoice_payment_state, 'paid')

    def test_inv_refund_foreign_payment_writeoff_domestic5(self):
        """
                    Receivable
                Domestic (Foreign)
        600.00 (600.00) |                    INV 1  > Done in foreign
                        |   250.00 (250.00)  INV 2  > Done in foreign
                        |   314.07 (314.07)  PAYMENT > Done in domestic (foreign non stored)
                        |    35.93  (60.93)  WriteOff > Done in domestic (foreign non stored). WriteOff is included in payment

        Reconciliation should be full, without exchange difference
        Invoices should be marked as paid
        """
        company = self.env.ref('base.main_company')
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id
        })

        inv1 = self._create_invoice(invoice_amount=600, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)
        inv2 = self._create_invoice(type="out_refund", invoice_amount=250, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        inv2_receivable = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertEqual(inv1_receivable.balance, 600.00)
        self.assertEqual(inv2_receivable.balance, -250)

        # partially pay the invoice with the refund
        inv1.js_assign_outstanding_line(inv2_receivable.id)
        self.assertEqual(inv1.amount_residual, 350)

        Payment = self.env['account.payment'].with_context(default_invoice_ids=[(4, inv1.id, False)])
        payment = Payment.create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_method_id': self.inbound_payment_method.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': inv1.partner_id.id,
            'amount': 314.07,
            'journal_id': self.bank_journal_euro.id,
            'company_id': company.id,
            'currency_id': self.currency_euro_id,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.diff_income_account.id,
        })
        payment.post()

        payment_receivable = payment.move_line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        self.assertEqual(payment_receivable.balance, -350)

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEquals(inv1_receivable.full_reconcile_id, inv2_receivable.full_reconcile_id)
        self.assertEquals(inv1_receivable.full_reconcile_id, payment_receivable.full_reconcile_id)

        self.assertFalse(inv1_receivable.full_reconcile_id.exchange_move_id)

        self.assertEquals(inv1.invoice_payment_state, 'paid')
        self.assertEquals(inv2.invoice_payment_state, 'paid')

    def test_inv_refund_foreign_payment_writeoff_domestic6(self):
        """
                    Receivable
                Domestic (Foreign)
        540.25 (600.00) |                    INV 1  > Done in foreign
                        |   225.10 (250.00)  INV 2  > Done in foreign
                        |   315.15 (350.00)  PAYMENT > Done in domestic (the 350.00 is virtual, non stored)
        """
        company = self.env.ref('base.main_company')
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.1106,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id
        })
        inv1 = self._create_invoice(invoice_amount=600, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)
        inv2 = self._create_invoice(type="out_refund", invoice_amount=250, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        inv2_receivable = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertEqual(inv1_receivable.balance, 540.25)
        self.assertEqual(inv2_receivable.balance, -225.10)

        # partially pay the invoice with the refund
        inv1.js_assign_outstanding_line(inv2_receivable.id)
        self.assertAlmostEqual(inv1.amount_residual, 350)
        self.assertAlmostEqual(inv1_receivable.amount_residual, 315.15)

        Payment = self.env['account.payment']
        payment = Payment.create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_method_id': self.inbound_payment_method.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': inv1.partner_id.id,
            'amount': 314.07,
            'journal_id': self.bank_journal_euro.id,
            'company_id': company.id,
            'currency_id': self.currency_euro_id,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.diff_income_account.id,
            'invoice_ids': [(4, inv1.id, False)],
        })
        payment.post()

        payment_receivable = payment.move_line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEquals(inv1_receivable.full_reconcile_id, inv2_receivable.full_reconcile_id)
        self.assertEquals(inv1_receivable.full_reconcile_id, payment_receivable.full_reconcile_id)

        exchange_rcv = inv1_receivable.full_reconcile_id.exchange_move_id.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        self.assertEqual(exchange_rcv.amount_currency, 0.01)

        self.assertEquals(inv1.invoice_payment_state, 'paid')
        self.assertEquals(inv2.invoice_payment_state, 'paid')

    def test_inv_refund_foreign_payment_writeoff_domestic6bis(self):
        """
        Same as domestic6, but only in foreign currencies
        Obviously, it should lead to the same kind of results
        Here there is no exchange difference entry though
        """
        foreign_0 = self.env['res.currency'].create({
            'name': 'foreign0',
            'symbol': 'F0'
        })
        foreign_1 = self.env['res.currency'].browse(self.currency_usd_id)

        company = self.env.ref('base.main_company')
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })

        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': foreign_0.id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.1106,  # Don't change this !
            'currency_id': foreign_1.id,
            'company_id': self.env.ref('base.main_company').id
        })
        inv1 = self._create_invoice(invoice_amount=600, currency_id=foreign_1.id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)
        inv2 = self._create_invoice(type="out_refund", invoice_amount=250, currency_id=foreign_1.id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        inv2_receivable = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertEqual(inv1_receivable.balance, 540.25)
        self.assertEqual(inv2_receivable.balance, -225.10)

        # partially pay the invoice with the refund
        inv1.js_assign_outstanding_line(inv2_receivable.id)
        self.assertAlmostEqual(inv1.amount_residual, 350)
        self.assertAlmostEqual(inv1_receivable.amount_residual, 315.15)

        Payment = self.env['account.payment'].with_context(default_invoice_ids=[(4, inv1.id, False)])
        payment = Payment.create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_method_id': self.inbound_payment_method.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': inv1.partner_id.id,
            'amount': 314.07,
            'journal_id': self.bank_journal_euro.id,
            'company_id': company.id,
            'currency_id': foreign_0.id,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.diff_income_account.id,
            'invoice_ids': [(4, inv1.id, False)],
        })
        payment.post()

        payment_receivable = payment.move_line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEquals(inv1_receivable.full_reconcile_id, inv2_receivable.full_reconcile_id)
        self.assertEquals(inv1_receivable.full_reconcile_id, payment_receivable.full_reconcile_id)

        self.assertFalse(inv1_receivable.full_reconcile_id.exchange_move_id)

        self.assertEquals(inv1.invoice_payment_state, 'paid')
        self.assertEquals(inv2.invoice_payment_state, 'paid')

    def test_inv_refund_foreign_payment_writeoff_domestic7(self):
        """
                    Receivable
                Domestic (Foreign)
        5384.48 (5980.00) |                      INV 1  > Done in foreign
                          |   5384.43 (5979.95)  PAYMENT > Done in domestic (foreign non stored)
                          |      0.05    (0.00)  WriteOff > Done in domestic (foreign non stored). WriteOff is included in payment,
                                                                so, the amount in currency is irrelevant

        Reconciliation should be full, without exchange difference
        Invoices should be marked as paid
        """
        company = self.env.ref('base.main_company')
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.1106,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id
        })
        inv1 = self._create_invoice(invoice_amount=5980, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertAlmostEqual(inv1_receivable.balance, 5384.48)

        Payment = self.env['account.payment']
        payment = Payment.create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_method_id': self.inbound_payment_method.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': inv1.partner_id.id,
            'amount': 5384.43,
            'journal_id': self.bank_journal_euro.id,
            'company_id': company.id,
            'currency_id': self.currency_euro_id,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.diff_income_account.id,
            'invoice_ids': [(4, inv1.id, False)],
        })
        payment.post()

        payment_receivable = payment.move_line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEquals(inv1_receivable.full_reconcile_id, payment_receivable.full_reconcile_id)

        self.assertFalse(inv1_receivable.full_reconcile_id.exchange_move_id)

        self.assertEquals(inv1.invoice_payment_state, 'paid')

    def test_inv_refund_foreign_payment_writeoff_domestic8(self):
        """
        Roughly the same as *_domestic7
        Though it simulates going through the reconciliation widget
        Because the WriteOff is on a different line than the payment
        """
        company = self.env.ref('base.main_company')
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.1106,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': self.env.ref('base.main_company').id
        })
        inv1 = self._create_invoice(invoice_amount=5980, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertAlmostEqual(inv1_receivable.balance, 5384.48)

        Payment = self.env['account.payment']
        payment = Payment.create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_method_id': self.inbound_payment_method.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': inv1.partner_id.id,
            'amount': 5384.43,
            'journal_id': self.bank_journal_euro.id,
            'company_id': company.id,
            'currency_id': self.currency_euro_id,
        })
        payment.post()
        payment_receivable = payment.move_line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        move_balance = self.env['account.move'].create({
            'partner_id': inv1.partner_id.id,
            'date': time.strftime('%Y') + '-07-15',
            'journal_id': self.bank_journal_usd.id,
            'line_ids': [
                (0, False, {'credit': 0.05, 'account_id': inv1_receivable.account_id.id, 'name': 'Balance WriteOff'}),
                (0, False, {'debit': 0.05, 'account_id': self.diff_expense_account.id, 'name': 'Balance WriteOff'}),
            ]
        })
        move_balance.post()
        move_balance_receiv = move_balance.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        (inv1_receivable + payment_receivable + move_balance_receiv).reconcile()

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEquals(inv1_receivable.full_reconcile_id, payment_receivable.full_reconcile_id)
        self.assertEqual(move_balance_receiv.full_reconcile_id, inv1_receivable.full_reconcile_id)

        exchange_rcv = inv1_receivable.full_reconcile_id.exchange_move_id.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        self.assertEqual(exchange_rcv.amount_currency, 0.01)

        self.assertEquals(inv1.invoice_payment_state, 'paid')
