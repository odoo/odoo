from openerp.tests.common import TransactionCase
from openerp.tools import float_compare
import time

class TestBankReconciliation(TransactionCase):
    """ Test various use cases of bank statement reconciliation """

    def setUp(self):
        super(TestBankReconciliation, self).setUp()
        # Get models
        self.account_invoice_model = self.registry('account.invoice')
        self.account_move_model = self.registry('account.move')
        self.account_invoice_line_model = self.registry('account.invoice.line')
        self.acc_bank_stmt_model = self.registry('account.bank.statement')
        self.acc_bank_stmt_line_model = self.registry('account.bank.statement.line')
        self.account_tax_model = self.registry('account.tax')
        # Get records
        self.partner_agrolait_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "base", "res_partner_2")[1]
        self.account_rcv_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "a_recv")[1]
        self.account_rsa_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "rsa")[1]
        self.product_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "product", "product_product_4")[1]
        self.bank_journal_euro_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "bank_journal")[1]
        self.account_euro_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "bnk")[1]
        self.period_7_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "period_7")[1]
        self.account_input_vat_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "iva")[1]
        # Create a 15% tax
        self.tax_15_percent_id = self.account_tax_model.create(self.cr, self.uid, {
            'name': '15%',
            'amount': 0.15,
            'account_paid_id': self.account_input_vat_id,
            'account_analytic_collected_id': self.account_input_vat_id
        })

    def create_invoice(self, amount, inv_type='out_invoice'):
        """ Create and open an invoice ; return the record
        """
        invoice_id = self.account_invoice_model.create(self.cr, self.uid, {
            'partner_id': self.partner_agrolait_id,
            'reference_type': 'none',
            'name': inv_type == 'out_invoice' and 'customer invoice' or 'supplier invoice',
            'account_id': self.account_rcv_id,
            'type': inv_type,
            'date_invoice': time.strftime('%Y') + '-07-15',
        })
        self.account_invoice_line_model.create(self.cr, self.uid, {
            'product_id': self.product_id,
            'quantity': 1,
            'price_unit': amount,
            'invoice_id': invoice_id,
            'name': 'something',
        })
        self.registry('account.invoice').signal_workflow(self.cr, self.uid, [invoice_id], 'invoice_open')
        invoice_record = self.account_invoice_model.browse(self.cr, self.uid, [invoice_id])
        return invoice_record

    def create_statement_line(self, amount):
        """ Create a one-line bank statement ; return the statement line
        """
        bank_stmt_id = self.acc_bank_stmt_model.create(self.cr, self.uid, {
            'journal_id': self.bank_journal_euro_id,
            'date': time.strftime('%Y') + '-07-15',
        })
        bank_stmt_line_id = self.acc_bank_stmt_line_model.create(self.cr, self.uid, {
            'name': 'payment',
            'statement_id': bank_stmt_id,
            'partner_id': self.partner_agrolait_id,
            'amount': amount,
            'date': time.strftime('%Y') + '-07-15',
        })
        st_line_record = self.acc_bank_stmt_line_model.browse(self.cr, self.uid, [bank_stmt_line_id])
        return st_line_record

    def check_results(self, move, aml_dicts):
        """ Check that lines of the move are consistent with the aml_dicts (indexed by account_id)
        """
        self.assertEquals(len(move.line_id), len(aml_dicts))
        for move_line in move.line_id:
            dict = aml_dicts[move_line.account_id.id]
            self.assertEquals(round(move_line.debit, 2), dict['debit'])
            self.assertEquals(round(move_line.credit, 2), dict['credit'])

    def get_move_line(self, move, predicate):
        for line in move.line_id:
            if predicate(line):
                return line
        return None

    def test_reconcile_with_writeoff_and_tax(self):
        # Create an invoice, a statement line and reconcile it with the invoice and a write-off on which is applied a tax
        inv = self.create_invoice(50)
        aml_a_rcv = self.get_move_line(inv.move_id, lambda line: line.account_id.id == self.account_rcv_id)
        st_line = self.create_statement_line(61.5)
        self.account_tax_model.browse(self.cr, self.uid, [self.tax_15_percent_id]).price_include = False
        move_id = self.acc_bank_stmt_line_model.process_reconciliation(self.cr, self.uid, st_line.id, [
            {'counterpart_move_line_id': aml_a_rcv.id, 'debit': 0.0, 'credit': 50, 'name': aml_a_rcv.name},
            {'account_id': self.account_rsa_id, 'debit': 0.0, 'credit': 10, 'name': 'w/o', 'account_tax_id': self.tax_15_percent_id}
        ])

        # Check the invoice is reconciled and the reconciliation move is correct
        self.assertTrue(inv.reconciled)
        self.check_results(
            self.account_move_model.browse(self.cr, self.uid, [move_id]),
            {
                self.account_euro_id: {'debit': 61.5, 'credit': 0.0}, # aml from the statement line
                self.account_rcv_id: {'debit': 0.0, 'credit': 50.0}, # aml to reconcile the invoice
                self.account_rsa_id: {'debit': 0.0, 'credit': 10.0}, # writeoff aml
                self.account_input_vat_id: {'debit': 0.0, 'credit': 1.5}, # writeoff tax aml
            }
        )

    def test_reconcile_with_writeoff_and_tax_included(self):
        # Create a statement line an reconcile it with a writeoff on which is applied a tax included in price
        st_line = self.create_statement_line(92)
        self.account_tax_model.browse(self.cr, self.uid, [self.tax_15_percent_id]).price_include = True
        move_id = self.acc_bank_stmt_line_model.process_reconciliation(self.cr, self.uid, st_line.id, [
            {'account_id': self.account_rsa_id, 'debit': 0.0, 'credit': 92, 'name': 'w/o', 'account_tax_id': self.tax_15_percent_id}
        ])

        # Check the reconciliation move is correct
        self.check_results(
            self.account_move_model.browse(self.cr, self.uid, [move_id]),
            {
                self.account_euro_id: {'debit': 92, 'credit': 0.0}, # aml from the statement line
                self.account_rsa_id: {'debit': 0.0, 'credit': 80.0}, # writeoff aml
                self.account_input_vat_id: {'debit': 0.0, 'credit': 12.0}, # writeoff tax aml
            }
        )

    def test_reconcile_partial(self):
        # Create an invoice of 100, a statement line of 50 and partially reconcile the invoice with it
        inv = self.create_invoice(100)
        aml_a_rcv = self.get_move_line(inv.move_id, lambda line: line.account_id.id == self.account_rcv_id)
        st_line = self.create_statement_line(50)
        move_id = self.acc_bank_stmt_line_model.process_reconciliation(self.cr, self.uid, st_line.id, [
            {'counterpart_move_line_id': aml_a_rcv.id, 'debit': 0.0, 'credit': 50, 'name': aml_a_rcv.name}
        ])

        # Check the invoice has a residual amount of 50 and the reconciliation move contains a partially reconciled move line in the receivable account
        self.assertFalse(inv.reconciled)
        self.assertAlmostEqual(inv.residual, 50)
        aml_reconcile_inv = self.get_move_line(
            self.account_move_model.browse(self.cr, self.uid, [move_id]),
            lambda line: float_compare(line.debit, 50, precision_digits=2)
        )
        self.assertIsNotNone(aml_reconcile_inv)
        self.assertEqual(len(aml_reconcile_inv.reconcile_partial_id.line_partial_ids), 2)

    def test_reconcile_with_existing_payment(self):
        # Create an invoice, pay it, create a statement line and reconcile it with the invoice parment line
        inv = self.create_invoice(50)
        self.account_invoice_model.pay_and_reconcile(self.cr, self.uid, [inv.id], 50, self.account_rcv_id, self.period_7_id, self.bank_journal_euro_id, None, None, None)
        aml_payment = inv.payment_ids[0]
        self.assertFalse(aml_payment.statement_id)
        st_line = self.create_statement_line(50)
        move_id = self.acc_bank_stmt_line_model.process_reconciliation(self.cr, self.uid, st_line.id, [
            {'counterpart_move_line_id': aml_payment.id, 'already_paid': True, 'debit': 0.0, 'credit': 50, 'name': aml_payment.name},
        ])

        # Check the reconciliation didn't create a move, linked the payment line to the statement and linked the statement line to the payment move
        self.assertIsNone(move_id)
        self.assertTrue(aml_payment.statement_id)
        self.assertEqual(st_line.journal_entry_ids[0].id, aml_payment.move_id.id)
