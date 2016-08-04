from odoo.addons.account.tests.account_test_classes import AccountingTestCase

class TestBankStatementReconciliation(AccountingTestCase):

    def setUp(self):
        super(TestBankStatementReconciliation, self).setUp()
        self.i_model = self.env['account.invoice']
        self.il_model = self.env['account.invoice.line']
        self.bs_model = self.env['account.bank.statement']
        self.bsl_model = self.env['account.bank.statement.line']
        self.partner_agrolait = self.env.ref("base.res_partner_2")

    def test_reconciliation_proposition(self):
        rcv_mv_line = self.create_invoice(100)
        st_line = self.create_statement_line(100)

        # exact amount match
        rec_prop = st_line.get_reconciliation_proposition()
        self.assertEqual(len(rec_prop), 1)
        self.assertEqual(rec_prop[0].id, rcv_mv_line.id)

    def test_full_reconcile(self):
        rcv_mv_line = self.create_invoice(100)
        st_line = self.create_statement_line(100)
        # reconcile
        st_line.process_reconciliation(counterpart_aml_dicts=[{
            'move_line': rcv_mv_line,
            'credit': 100,
            'debit': 0,
            'name': rcv_mv_line.name,
        }])

        # check everything went as expected
        rec_move = st_line.journal_entry_ids[0]
        self.assertTrue(rec_move)
        counterpart_mv_line = None
        for l in rec_move.line_ids:
            if l.account_id.user_type_id.type == 'receivable':
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
        vals = {'partner_id': self.partner_agrolait.id,
                'type': 'out_invoice',
                'name': '-',
                'currency_id': self.env.user.company_id.currency_id.id,
                }
        # new creates a temporary record to apply the on_change afterwards
        invoice = self.i_model.new(vals)
        invoice._onchange_partner_id()
        vals.update({'account_id': invoice.account_id.id})
        invoice = self.i_model.create(vals)

        self.il_model.create({
            'quantity': 1,
            'price_unit': amount,
            'invoice_id': invoice.id,
            'name': '.',
            'account_id': self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1).id,
        })
        invoice.action_invoice_open()

        mv_line = None
        for l in invoice.move_id.line_ids:
            if l.account_id.id == vals['account_id']:
                mv_line = l
        self.assertIsNotNone(mv_line)

        return mv_line

    def create_statement_line(self, st_line_amount):
        journal = self.bs_model.with_context(journal_type='bank')._default_journal()
        #journal = self.env.ref('l10n_be.bank_journal')
        bank_stmt = self.bs_model.create({'journal_id': journal.id})

        bank_stmt_line = self.bsl_model.create({
            'name': '_',
            'statement_id': bank_stmt.id,
            'partner_id': self.partner_agrolait.id,
            'amount': st_line_amount,
            })

        return bank_stmt_line
