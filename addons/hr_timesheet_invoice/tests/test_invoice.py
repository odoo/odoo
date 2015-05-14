from openerp.addons.account.tests.account_test_classes import AccountingTestCase

class TestInvoice(AccountingTestCase):
    """Tests to generate invoices from analytic lines
    """

    def setUp(self):
        super(TestInvoice, self).setUp()
        cr, uid = self.cr, self.uid

        self.account_invoice = self.registry('account.invoice')
        self.account_analytic_account = self.registry('account.analytic.account')
        self.account_analytic_line = self.registry('account.analytic.line')
        self.product_product = self.registry('product.product')

        self.think_big_id = self.registry("ir.model.data").get_object_reference(cr, uid, "base", "res_partner_18")[1]
        self.timesheet_journal_id = self.registry("ir.model.data").get_object_reference(cr, uid, "hr_timesheet", "analytic_journal")[1]
        self.expense_journal_id = self.registry("ir.model.data").get_object_reference(cr, uid, 'account', 'exp')[1]
        user_type_id = self.ref('account.data_account_type_expenses')
        self.expense_account_id = self.env['account.account'].create({'code': 'X2120', 'name': 'Test Expense Account', 'user_type_id': user_type_id}).id
        self.factor_100_id = self.registry("ir.model.data").get_object_reference(cr, uid, "hr_timesheet_invoice", "timesheet_invoice_factor1")[1]

        self.potato_account_id = self.account_analytic_account.create(cr, uid, {
            'name': 'Potatoes Project',
            'partner_id': self.think_big_id,
            'type': 'contract',
            'state': 'open',
        })
        self.carrot_account_id = self.account_analytic_account.create(cr, uid, {
            'name': 'Carrot & Development',
            'partner_id': self.think_big_id,
            'type': 'contract',
            'state': 'open',
        })
        self.potato_id = self.product_product.create(cr, uid, {
            'name': 'Potato',
            'list_price': 2,
        })
        self.carrot_id = self.product_product.create(cr, uid, {
            'name': 'Carrot',
            'list_price': 3,
        })

    def test_single_invoice(self):
        cr, uid = self.cr, self.uid
        first_line = {
            'name': 'One potato',
            'amount': 2,
            'unit_amount': 1,
            'product_id': self.potato_id,
            'account_id': self.potato_account_id,
            'general_account_id': self.expense_account_id,
            'journal_id': self.expense_journal_id,
            'partner_id': self.think_big_id,
            'to_invoice': self.factor_100_id,
        }
        second_line = {
            'name': 'Two carrots',
            'amount': 6,
            'unit_amount': 2,
            'product_id': self.carrot_id,
            'account_id': self.carrot_account_id,
            'general_account_id': self.expense_account_id,
            'journal_id': self.expense_journal_id,
            'partner_id': self.think_big_id,
            'to_invoice': self.factor_100_id,
        }
        first_line_id = self.account_analytic_line.create(cr, uid, first_line)
        second_line_id = self.account_analytic_line.create(cr, uid, second_line)

        data = {'group_by_partner': False, 'date': True, 'name': True}
        invoice_ids = self.account_analytic_line.invoice_cost_create(cr, uid, [first_line_id, second_line_id], data)
        self.assertEquals(len(invoice_ids), 2)
        for invoice in self.account_invoice.browse(cr, uid, invoice_ids[0]):
            self.assertEquals(len(invoice.invoice_line_ids), 1)
            line = invoice.invoice_line_ids[0]
            if line.product_id.id == self.potato_id:
                self.assertEquals(line.account_analytic_id.id, self.potato_account_id)
                self.assertEquals(line.price_unit, -2)
                self.assertEquals(line.quantity, 1)
            else:
                self.assertEquals(line.product_id.id, self.carrot_id)
                self.assertEquals(line.account_analytic_id.id, self.carrot_account_id)
                self.assertEquals(line.price_unit, -3)
                self.assertEquals(line.quantity, 2)

        data = {'group_by_partner': True, 'date': True, 'name': True}
        first_line_id = self.account_analytic_line.create(cr, uid, first_line)
        second_line_id = self.account_analytic_line.create(cr, uid, second_line)
        invoice_ids = self.account_analytic_line.invoice_cost_create(cr, uid, [first_line_id, second_line_id], data)
        self.assertEquals(len(invoice_ids), 1)
        invoice = self.account_invoice.browse(cr, uid, invoice_ids[0])
        self.assertEquals(len(invoice.invoice_line_ids), 2)
        for line in invoice.invoice_line_ids:
            if line.product_id.id == self.potato_id:
                self.assertEquals(line.account_analytic_id.id, self.potato_account_id)
                self.assertEquals(line.price_unit, -2)
                self.assertEquals(line.quantity, 1)
            else:
                self.assertEquals(line.product_id.id, self.carrot_id)
                self.assertEquals(line.account_analytic_id.id, self.carrot_account_id)
                self.assertEquals(line.price_unit, -3)
                self.assertEquals(line.quantity, 2)
