from openerp.tests.common import TransactionCase

class TestBankStatementReconciliation(TransactionCase):

    def setUp(self):
        super(TestBankStatementReconciliation, self).setUp()
        self.i_model = self.env['account.invoice']
        self.il_model = self.env['account.invoice.line']
        self.bs_model = self.env['account.bank.statement']
        self.bsl_model = self.env['account.bank.statement.line']

        self.partner_agrolait = self.env.ref("base.res_partner_2")
        self.account_rcv = self.env.ref("account.a_recv")
        self.bank_journal = self.env.ref('account.bank_journal')
        self.bank_account = self.env.ref('account.bnk')

    def test_reconciliation_proposition(self):
        rcv_mv_line = self.create_invoice(100)
        st_line = self.create_statement_line(100)

        # exact amount match
        rec_prop = st_line.get_reconciliation_proposition()
        self.assertEqual(len(rec_prop), 1)
        self.assertEqual(rec_prop[0]['id'], rcv_mv_line.id)

    def test_full_reconcile(self):
        rcv_mv_line = self.create_invoice(100)
        st_line = self.create_statement_line(100)

        # reconcile
        st_line.process_reconciliation([{
            'counterpart_move_line_id': rcv_mv_line.id,
            'is_reconciled': False,
            'credit': 100,
            'debit': 0,
            'name': rcv_mv_line.name,
        }])

        # check everything went as expected
        rec_move = st_line.journal_entry_id
        self.assertTrue(rec_move)
        counterpart_mv_line = None
        for l in rec_move.line_id:
            if l.account_id.id == self.account_rcv.id:
                counterpart_mv_line = l
                break
        self.assertIsNotNone(counterpart_mv_line)
        self.assertTrue(rcv_mv_line.reconciled)
        self.assertTrue(counterpart_mv_line.reconciled)
        self.assertEqual(counterpart_mv_line.matched_credit_ids, rcv_mv_line.matched_debit_ids)

    def test_reconcile_with_write_off(self):
        pass

    def create_invoice(self, amount):
        """ Return the move line that gets to be reconciled (the one in the receivable account) """

        invoice = self.i_model.create({
            'partner_id': self.partner_agrolait.id,
            'name': '-',
            'account_id': self.account_rcv.id,
            'type': 'out_invoice', })
        self.il_model.create({
            'quantity': 1,
            'price_unit': amount,
            'invoice_id': invoice.id,
            'name': '.', })
        invoice.signal_workflow('invoice_open')

        mv_line = None
        for l in invoice.move_id.line_id:
            if l.account_id.id == self.account_rcv.id:
                mv_line = l
        self.assertIsNotNone(mv_line)

        return mv_line

    def create_statement_line(self, st_line_amount):
        bank_stmt = self.bs_model.create({
            'journal_id': self.bank_journal.id, })
        bank_stmt_line = self.bsl_model.create({
            'name': '_',
            'statement_id': bank_stmt.id,
            'partner_id': self.partner_agrolait.id,
            'amount': st_line_amount, })
        return bank_stmt_line
