from openerp.addons.account.tests.account_test_invoices import AccountTestInvoices
from openerp.tests.common import TransactionCase
from openerp.tools import float_compare
import time


class TestTax(AccountTestInvoices):

    def setUp(self):
        super(TestTax, self).setUp()

        self.fixed_tax = self.tax_model.create({
            'name': "Fixed tax",
            'amount_type': 'fixed',
            'amount': 10,
            'sequence': 1,
        })
        self.fixed_tax_bis = self.tax_model.create({
            'name': "Fixed tax bis",
            'amount_type': 'fixed',
            'amount': 15,
            'sequence': 2,
        })
        self.percent_tax = self.tax_model.create({
            'name': "Percent tax",
            'amount_type': 'percent',
            'amount': 10,
            'sequence': 3,
        })
        self.division_tax = self.tax_model.create({
            'name': "Division tax",
            'amount_type': 'division',
            'amount': 10,
            'sequence': 4,
        })
        self.group_tax = self.tax_model.create({
            'name': "Group tax",
            'amount_type': 'group',
            'amount': 0,
            'sequence': 5,
            'children_tax_ids': [
                (4, self.fixed_tax.id, 0),
                (4, self.percent_tax.id, 0)
            ]
        })
        self.group_tax_bis = self.tax_model.create({
            'name': "Group tax bis",
            'amount_type': 'group',
            'amount': 0,
            'sequence': 6,
            'children_tax_ids': [
                (4, self.fixed_tax.id, 0),
                (4, self.percent_tax.id, 0)
            ]
        })
        self.group_of_group_tax = self.tax_model.create({
            'name': "Group of group tax",
            'amount_type': 'group',
            'amount': 0,
            'sequence': 7,
            'children_tax_ids': [
                (4, self.group_tax.id, 0),
                (4, self.group_tax_bis.id, 0)
            ]
        })
        self.bank_journal = self.env['account.journal'].search([('type', '=', 'bank'), ('company_id', '=', self.account_manager.company_id.id)])[0]
        self.bank_account = self.bank_journal.default_debit_account_id
        self.expense_account = self.env['account.account'].search([('user_type_id.type', '=', 'payable')], limit=1)  # Should be done by onchange later

    def test_tax_group_not_included_in_base_amount_reporting_setup(self):
        self.fixed_tax.include_base_amount = True
        self.percent_tax.include_base_amount = False
        self.group_tax.include_base_amount = False
        self.group_tax.sequence = 1
        self.fixed_tax_bis.include_base_amount = False
        self.account_invoice_purchase.invoice_line_ids[0].write({
            'invoice_line_tax_ids': [(6, 0, [
                self.group_tax.id,
                self.fixed_tax_bis.id])]
        })
        # We construct a dictionary representing the expected results of tax_ids
        # depending on the value of tax_line_id or product_id of the aml
        tax_ids_expected_result = {
            # First Tax (Group Tax): (self.fixed_tax.sequence == 1 and self.group_tax.sequence == 1) == True
            # Therefore, there is no tax before this that could have been included in its base amount
            self.fixed_tax: self.tax_model.browse([]),
            # Second Tax (Group Tax): As (self.percent_tax.sequence == 3) within self.group_tax, this is the 2nd tax
            # As we are within the group and First Tax is an include-base-amount tax,
            # First Tax should be found among tax_ids of Second Tax aml ("taken into account in the fiscal report base amount")
            self.percent_tax: self.fixed_tax,
            # Third Tax (Single Tax): self.fixed_tax_bis is ordered last, as (self.group_tax.sequence == 1
            # and self.fixed_tax_bis.sequence == 2) ... (see tax group ordering)
            # However, as self.group_tax has been set to NOT be included into subsequent taxes,
            # albeit some of its members (First Tax) are, we should not find any tax on tax_ids here.
            self.fixed_tax_bis: self.tax_model.browse([]),
            # The product line should contain all taxes (group, children and standalone taxes) on tax_ids
            # This way base values in the fiscal report are shown consistently.
            self.invoice_line_product: self.fixed_tax | self.fixed_tax_bis | self.percent_tax | self.group_tax,
        }
        # Validate the invoice.
        self.account_invoice_purchase.signal_workflow('invoice_open')
        for aml in self.account_invoice_purchase.move_id.line_ids:
            if aml.tax_line_id:
                self.assertItemsEqual(aml.tax_ids, tax_ids_expected_result[aml.tax_line_id])
            if aml.product_id:
                self.assertItemsEqual(aml.tax_ids, tax_ids_expected_result[aml.product_id])

    def test_tax_group_of_group_tax(self):
        self.fixed_tax.include_base_amount = True
        self.group_tax.include_base_amount = True
        self.group_of_group_tax.include_base_amount = True
        res = self.group_of_group_tax.compute_all(200.0)
        self.assertEquals(res['total_excluded'], 200.0)
        # After calculation of first group
        # base = 210
        # total_included = 231
        # Base of the first grouped is passed
        # Base after the second group (220) is dropped.
        # Base of the group of groups is passed out,
        # so we obtain base as after first group
        self.assertEquals(res['base'], 210.0)
        self.assertEquals(res['total_included'], 263.0)

    def test_tax_group(self):
        res = self.group_tax.compute_all(200.0)
        self.assertEquals(res['total_excluded'], 200.0)
        self.assertEquals(res['total_included'], 230.0)
        self.assertEquals(len(res['taxes']), 2)
        self.assertEquals(res['taxes'][0]['amount'], 10.0)
        self.assertEquals(res['taxes'][1]['amount'], 20.0)

    def test_tax_percent_division(self):
        self.division_tax.price_include = True
        self.division_tax.include_base_amount = True
        self.percent_tax.price_include = False
        self.percent_tax.include_base_amount = False
        res_division = self.division_tax.compute_all(200.0)
        res_percent = self.percent_tax.compute_all(200.0)
        self.assertEquals(res_division['taxes'][0]['amount'], 20.0)
        self.assertEquals(res_percent['taxes'][0]['amount'], 20.0)
        self.division_tax.price_include = False
        self.division_tax.include_base_amount = False
        self.percent_tax.price_include = True
        self.percent_tax.include_base_amount = True
        res_division = self.division_tax.compute_all(200.0)
        res_percent = self.percent_tax.compute_all(200.0)
        self.assertEquals(res_division['taxes'][0]['amount'], 22.22)
        self.assertEquals(res_percent['taxes'][0]['amount'], 18.18)

    def test_tax_sequence_normalized_set(self):
        self.division_tax.sequence = 1
        self.fixed_tax.sequence = 2
        self.percent_tax.sequence = 3
        taxes_set = (self.group_tax | self.division_tax)
        res = taxes_set.compute_all(200.0)
        self.assertEquals(res['taxes'][0]['amount'], 22.22)
        self.assertEquals(res['taxes'][1]['amount'], 10.0)
        self.assertEquals(res['taxes'][2]['amount'], 20.0)

    def test_tax_include_base_amount(self):
        self.fixed_tax.include_base_amount = True
        res = self.group_tax.compute_all(200.0)
        self.assertEquals(res['total_included'], 231.0)

    def test_tax_currency(self):
        self.division_tax.amount = 15.0
        res = self.division_tax.compute_all(200.0, currency=self.env.ref('base.VEF'))
        self.assertAlmostEqual(res['total_included'], 235.2941)

    def test_tax_move_lines_creation(self):
        """ Test that creating a move.line with tax_ids generates the tax move lines and adjust line amount when a tax is price_include """

        self.fixed_tax.price_include = True
        self.fixed_tax.include_base_amount = True
        company_id = self.env['res.users'].browse(self.env.uid).company_id.id
        vals = {
            'date': time.strftime('%Y-01-01'),
            'journal_id': self.bank_journal.id,
            'name': 'Test move',
            'line_ids': [(0, 0, {
                    'account_id': self.bank_account.id,
                    'debit': 235,
                    'credit': 0,
                    'name': 'Bank Fees',
                    'partner_id': False,
            }), (0, 0, {
                'account_id': self.expense_account.id,
                'debit': 0,
                'credit': 200,
                'date': time.strftime('%Y-01-01'),
                'name': 'Bank Fees',
                'partner_id': False,
                'tax_ids': [(4, self.group_tax.id), (4, self.fixed_tax_bis.id)]
            })],
            'company_id': company_id,
        }
        move = self.env['account.move'].create(vals)

        aml_fixed_tax = move.line_ids.filtered(lambda l: l.tax_line_id.id == self.fixed_tax.id)
        aml_percent_tax = move.line_ids.filtered(lambda l: l.tax_line_id.id == self.percent_tax.id)
        aml_fixed_tax_bis = move.line_ids.filtered(lambda l: l.tax_line_id.id == self.fixed_tax_bis.id)
        self.assertEquals(len(aml_fixed_tax), 1)
        self.assertEquals(aml_fixed_tax.credit, 10)
        self.assertEquals(len(aml_percent_tax), 1)
        self.assertEquals(aml_percent_tax.credit, 20)
        self.assertEquals(len(aml_fixed_tax_bis), 1)
        self.assertEquals(aml_fixed_tax_bis.credit, 15)

        aml_with_taxes = move.line_ids.filtered(lambda l: set(l.tax_ids.ids) == set([self.group_tax.id, self.fixed_tax_bis.id]))
        self.assertEquals(len(aml_with_taxes), 1)
        self.assertEquals(aml_with_taxes.credit, 190)
