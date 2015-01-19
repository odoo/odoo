from openerp.tests.common import TransactionCase
from openerp.tools import float_compare
import time

class TestBankReconciliation(TransactionCase):
    """ Test various use cases of bank statement reconciliation """

    def setUp(self):
        super(TestBankReconciliation, self).setUp()
        self.account_invoice_model = self.registry('account.invoice')
        self.account_move_model = self.registry('account.move')
        self.account_invoice_line_model = self.registry('account.invoice.line')
        self.acc_bank_stmt_model = self.registry('account.bank.statement')
        self.acc_bank_stmt_line_model = self.registry('account.bank.statement.line')
        self.account_tax_model = self.registry('account.tax')

        self.partner_agrolait_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "base", "res_partner_2")[1]
        self.account_rcv_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "a_recv")[1]
        self.account_rsa_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "rsa")[1]
        self.product_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "product", "product_product_4")[1]
        self.bank_journal_euro_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "bank_journal")[1]
        self.account_euro_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "bnk")[1]
        self.tax_15_percent_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "otaxs")[1]
        self.period_7_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "period_7")[1]

    def create_invoice(self, amount, inv_type='out_invoice'):
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

    def get_move_line(self, move, predicate):
        for line in move.line_id:
            if predicate(line):
                return line
        return None

    def test_reconcile_with_writeoff_and_tax(self):
        inv = self.create_invoice(50)
        aml_a_rcv = self.get_move_line(inv.move_id, lambda line: line.account_id.id == self.account_rcv_id)
        st_line = self.create_statement_line(61.5)
        self.account_tax_model.browse(self.cr, self.uid, [self.tax_15_percent_id]).price_include = False

        move_id = self.acc_bank_stmt_line_model.process_reconciliation(self.cr, self.uid, st_line.id, [
            {'counterpart_move_line_id': aml_a_rcv.id, 'debit': 0.0, 'credit': 50, 'name': aml_a_rcv.name},
            {'account_id': self.account_rsa_id, 'debit': 0.0, 'credit': 10, 'name': 'w/o', 'account_tax_id': self.tax_15_percent_id}
        ])
        move = self.account_move_model.browse(self.cr, self.uid, [move_id])

        self.assertTrue(inv.reconciled)

        aml_st_line = self.get_move_line(move, lambda line: float_compare(line.debit, 61.5, precision_digits=2))
        self.assertIsNotNone(aml_st_line)

        aml_reconcile_inv = self.get_move_line(move, lambda line: float_compare(line.credit, 50, precision_digits=2))
        self.assertIsNotNone(aml_reconcile_inv)

        aml_writeoff = self.get_move_line(move, lambda line: float_compare(line.credit, 50, precision_digits=2))
        self.assertIsNotNone(aml_writeoff)

        aml_tax = self.get_move_line(move, lambda line: float_compare(line.credit, 1.5, precision_digits=2))
        self.assertIsNotNone(aml_tax)

    def test_reconcile_with_writeoff_and_tax_included(self):
        st_line = self.create_statement_line(92)
        self.account_tax_model.browse(self.cr, self.uid, [self.tax_15_percent_id]).price_include = True
        
        move_id = self.acc_bank_stmt_line_model.process_reconciliation(self.cr, self.uid, st_line.id, [
            {'account_id': self.account_rsa_id, 'debit': 0.0, 'credit': 92, 'name': 'w/o', 'account_tax_id': self.tax_15_percent_id}
        ])
        move = self.account_move_model.browse(self.cr, self.uid, [move_id])

        aml_st_line = self.get_move_line(move, lambda line: float_compare(line.debit, 92, precision_digits=2))
        self.assertIsNotNone(aml_st_line)

        aml_writeoff = self.get_move_line(move, lambda line: float_compare(line.credit, 80, precision_digits=2))
        self.assertIsNotNone(aml_writeoff)

        aml_tax = self.get_move_line(move, lambda line: float_compare(line.credit, 12, precision_digits=2))
        self.assertIsNotNone(aml_tax)

    def test_reconcile_partial(self):
        inv = self.create_invoice(100)
        aml_a_rcv = self.get_move_line(inv.move_id, lambda line: line.account_id.id == self.account_rcv_id)
        st_line = self.create_statement_line(50)

        move_id = self.acc_bank_stmt_line_model.process_reconciliation(self.cr, self.uid, st_line.id, [
            {'counterpart_move_line_id': aml_a_rcv.id, 'debit': 0.0, 'credit': 50, 'name': aml_a_rcv.name}
        ])
        move = self.account_move_model.browse(self.cr, self.uid, [move_id])

        self.assertFalse(inv.reconciled)
        self.assertAlmostEqual(inv.residual, 50)

        aml_reconcile_inv = self.get_move_line(move, lambda line: float_compare(line.debit, 50, precision_digits=2))
        self.assertIsNotNone(aml_reconcile_inv)
        self.assertEqual(len(aml_reconcile_inv.reconcile_partial_id.line_partial_ids), 2)

    def test_reconcile_with_existing_payment(self):
        inv = self.create_invoice(50)
        self.account_invoice_model.pay_and_reconcile(self.cr, self.uid, [inv.id], 50, self.account_rcv_id, self.period_7_id, self.bank_journal_euro_id, None, None, None)
        aml_payment = inv.payment_ids[0]
        st_line = self.create_statement_line(50)

        move_id = self.acc_bank_stmt_line_model.process_reconciliation(self.cr, self.uid, st_line.id, [
            {'counterpart_move_line_id': aml_payment.id, 'already_paid': True, 'debit': 0.0, 'credit': 50, 'name': aml_payment.name},
        ])

        self.assertTrue(move_id == None)
        self.assertTrue(aml_payment.statement_id != False)
        self.assertTrue(st_line.journal_entry_ids[0].id == aml_payment.move_id.id)
