from odoo import Command
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestTdsTcsAlert(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ChartTemplate = cls.env['account.chart.template']

        # ==== Tax Groups ====
        # per transaction = 30000 and aggregate = 100000 and period = year and unit = total
        cls.tds_194c = ChartTemplate.ref('tds_group_194c')
        # per transaction = False and aggregate = 30000 and period = year and unit = total
        cls.tds_194j = ChartTemplate.ref('tds_group_194j')
        # per transaction = False and aggregate = 50000 and period = month and unit = total
        cls.tds_194ib = ChartTemplate.ref('tds_group_194ib')
        # per transaction = 5000000 and aggregate = False and period = year and unit = per_unit
        cls.tds_194ia = ChartTemplate.ref('tds_group_194ia')
        # per transaction = False and aggregate = 700000 and period = year and unit = total
        cls.tcs_206c1g_r = ChartTemplate.ref('tcs_group_206c1g_r')

        # ==== Chart of Accounts ====
        cls.purchase_account = ChartTemplate.ref('p2107')
        cls.purchase_account.write({
            'l10n_in_tds_tcs_section': cls.tds_194c.id
        })
        cls.house_expense_account = ChartTemplate.ref('p2103')
        cls.house_expense_account.write({
            'l10n_in_tds_tcs_section': cls.tds_194c.id
        })
        cls.internet_account = ChartTemplate.ref('p2105')
        cls.internet_account.write({
            'l10n_in_tds_tcs_section': cls.tds_194j.id
        })
        cls.rent_account = ChartTemplate.ref('p2111')
        cls.rent_account.write({
            'l10n_in_tds_tcs_section': cls.tds_194ib.id
        })
        cls.building_account = ChartTemplate.ref('p1011')
        cls.building_account.write({
            'l10n_in_tds_tcs_section': cls.tds_194ia.id
        })
        cls.sale_account = ChartTemplate.ref('p20011')
        cls.sale_account.write({
            'l10n_in_tds_tcs_section': cls.tcs_206c1g_r.id
        })
        cls.service_account = ChartTemplate.ref('p20021')
        cls.creditors_account = ChartTemplate.ref('p11211')

        # ==== Taxes ====
        cls.tax_194c = ChartTemplate.ref('tds_20_us_194c')
        cls.tax_194j = ChartTemplate.ref('tds_10_us_194j')
        cls.tax_194ia = ChartTemplate.ref('tds_20_us_194ia')
        cls.tax_194ib = ChartTemplate.ref('tds_20_us_194ib')
        cls.tax_206c1g_r = ChartTemplate.ref('tcs_5_us_206c_1g_som')

        country_in_id = cls.env.ref("base.in").id

        # ==== Partners ====
        cls.partner_a.write({
            'l10n_in_pan': 'ABCPM8965E'
        })
        cls.partner_b.write({
            'vat': '27ABCPM8965E1ZE',
            'l10n_in_pan': 'ABCPM8965E'
        })
        cls.partner_foreign_2 = cls.partner_foreign.copy()

        # ==== Company ====
        cls.default_company.write({
            'child_ids': [
                Command.create({
                    'name': 'Branch A',
                    "state_id": cls.env.ref("base.state_in_gj").id,
                    'account_fiscal_country_id': country_in_id,
                    'country_id': country_in_id,
                }),
                Command.create({
                    'name': 'Branch B',
                    "state_id": cls.env.ref("base.state_in_mh").id,
                    'account_fiscal_country_id': country_in_id,
                    'country_id': country_in_id,
                }),
                Command.create({
                    'name': 'Branch C',
                    "state_id": cls.env.ref("base.state_in_mp").id,
                    'account_fiscal_country_id': country_in_id,
                    'country_id': country_in_id,
                }),
            ],
        })
        cls.cr.precommit.run()  # load the CoA

        cls.branch_a, cls.branch_b, cls.branch_c = cls.env.company.child_ids

    def create_invoice(self, move_type=None, partner=None, invoice_date=None, amounts=None, taxes=None, company=None, accounts=None, quantities=None):
        invoice = self.init_invoice(
            move_type=move_type or 'in_invoice',
            partner=partner,
            invoice_date=invoice_date,
            post=False,
            amounts=amounts,
            company=company
        )

        for i, account in enumerate(accounts):
            invoice.invoice_line_ids[i].account_id = account.id

        if quantities:
            for i, quantity in enumerate(quantities):
                invoice.invoice_line_ids[i].quantity = quantity

        if taxes:
            for i, tax in enumerate(taxes):
                invoice.invoice_line_ids[i].tax_ids = tax.ids
        invoice.action_post()
        return invoice

    def reverse_move(self, move, date):
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=move.ids).create({
            'date': date,
            'reason': 'no reason',
            'journal_id': move.journal_id.id,
        })
        return move_reversal.refund_moves()

    def test_tcs_tds_warning(self):
        '''
        Test that if any of the limit is not exceeded.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-06-05',
            amounts=[29000],
            company=self.branch_a,
            accounts=[self.internet_account],
            quantities=[1]
        )

        self.assertEqual(move.l10n_in_tcs_tds_warning, False)

    def test_tcs_tds_warning_on_exceeded_per_transaction_limit(self):
        '''
        Test that if the per transaction limit is exceeded.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-06-05',
            amounts=[31000],
            company=self.branch_a,
            accounts=[self.purchase_account],
            quantities=[1]
        )
        line = move.invoice_line_ids[0]
        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")
        self.assertEqual(line.l10n_in_line_warning, True)

        move_1 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-06-05',
            amounts=[31000],
            company=self.branch_b,
            accounts=[self.purchase_account],
            quantities=[1]
        )
        line_1 = move_1.invoice_line_ids[0]
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")
        self.assertEqual(line_1.l10n_in_line_warning, True)

        move_2 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-06-05',
            amounts=[31000],
            taxes=[self.tax_194c],
            company=self.branch_b,
            accounts=[self.purchase_account],
            quantities=[1]
        )
        line_2 = move_2.invoice_line_ids[0]
        self.assertEqual(move_2.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_2.l10n_in_line_warning, False)

        move_3 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-06-05',
            amounts=[31000],
            taxes=[self.tax_194ia],
            company=self.branch_b,
            accounts=[self.purchase_account],
            quantities=[1]
        )
        line_3 = move_3.invoice_line_ids[0]
        self.assertEqual(move_3.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")
        self.assertEqual(line_3.l10n_in_line_warning, True)

    def test_tcs_tds_warning_on_monthly_aggregate_limit(self):
        '''
        Test the monthly aggregate limit, the warning
        message should be set accordingly.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-06-05',
            amounts=[30000],
            company=self.branch_a,
            accounts=[self.rent_account]
        )
        line = move.invoice_line_ids[0]
        self.assertEqual(move.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line.l10n_in_line_warning, False)

        move_1 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-07-06',
            amounts=[20000],
            company=self.branch_b,
            accounts=[self.rent_account]
        )
        line_1 = move_1.invoice_line_ids[0]
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_1.l10n_in_line_warning, False)

        move_2 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-07-16',
            amounts=[31000],
            company=self.branch_c,
            accounts=[self.rent_account]
        )
        line_2 = move_2.invoice_line_ids[0]
        self.assertEqual(move_2.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194IB on this transaction.")
        self.assertEqual(line_2.l10n_in_line_warning, True)

        move_3 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-09-06',
            amounts=[50000],
            company=self.branch_c,
            accounts=[self.rent_account]
        )
        line_3 = move_3.invoice_line_ids[0]
        self.assertEqual(move_3.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_3.l10n_in_line_warning, False)

        move_4 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-09-16',
            amounts=[50000],
            taxes=[self.tax_194ib],
            company=self.branch_c,
            accounts=[self.rent_account]
        )
        line_4 = move_4.invoice_line_ids[0]
        self.assertEqual(move_4.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_4.l10n_in_line_warning, False)

        move_5 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-05-16',
            amounts=[50000],
            taxes=[self.tax_194ib],
            company=self.branch_c,
            accounts=[self.rent_account]
        )
        line_5 = move_5.invoice_line_ids[0]
        self.assertEqual(move_5.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_5.l10n_in_line_warning, False)

    def test_tcs_tds_warning_per_unit_case(self):
        '''
        Test that if lines have the account which have
        the tcs/tds section with the per unit configuration
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-06-05',
            amounts=[6000000, 2600000, 5200000, 300000],
            company=self.branch_a,
            accounts=[self.building_account, self.building_account, self.building_account, self.building_account],
            quantities=[2, 2, 1, 1]
        )
        line_warning = [line.l10n_in_line_warning for line in move.invoice_line_ids]
        self.assertEqual(line_warning, [True, False, True, False])
        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194IA on this transaction.")

        move_1 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-06-05',
            amounts=[6000000, 2600000, 5200000, 300000],
            taxes=[self.tax_194ia, self.tax_194ia, self.tax_194ia, self.tax_194ia],
            company=self.branch_a,
            accounts=[self.building_account, self.building_account, self.building_account, self.building_account],
            quantities=[2, 2, 1, 1]
        )
        line_warning = [line.l10n_in_line_warning for line in move_1.invoice_line_ids]
        self.assertEqual(line_warning, [False, False, False, False])
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, False)

        move_2 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-06-05',
            amounts=[6000000, 5200000, 2600000],
            taxes=[self.tax_194ia, self.tax_194ia],
            company=self.branch_a,
            accounts=[self.building_account, self.building_account, self.building_account],
            quantities=[2, 1, 2]
        )
        line_warning = [line.l10n_in_line_warning for line in move_2.invoice_line_ids]
        self.assertEqual(line_warning, [False, False, False])
        self.assertEqual(move_2.l10n_in_tcs_tds_warning, False)

    def test_tcs_tds_warning_partner_wiht_pan(self):
        '''
        Test the aggregate limit when partner don't have
        pan number and having pan number.
        '''
        # no pan number
        move = self.create_invoice(
            partner=self.partner_foreign,
            invoice_date='2024-06-05',
            amounts=[30000],
            company=self.branch_a,
            accounts=[self.internet_account]
        )
        line = move.invoice_line_ids[0]
        self.assertEqual(move.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line.l10n_in_line_warning, False)

        move_1 = self.create_invoice(
            partner=self.partner_foreign_2,
            invoice_date='2024-06-05',
            amounts=[30000],
            company=self.branch_b,
            accounts=[self.internet_account]
        )
        line_1 = move_1.invoice_line_ids[0]
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_1.l10n_in_line_warning, False)

        # same pan number
        move_2 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-06-05',
            amounts=[30000],
            company=self.branch_a,
            accounts=[self.internet_account]
        )
        line_2 = move_2.invoice_line_ids[0]
        self.assertEqual(move_2.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_2.l10n_in_line_warning, False)

        move_3 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-06-05',
            amounts=[30000],
            company=self.branch_b,
            accounts=[self.internet_account]
        )
        line_3 = move_3.invoice_line_ids[0]
        self.assertEqual(move_3.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194J on this transaction.")
        self.assertEqual(line_3.l10n_in_line_warning, True)

    def test_tcs_tds_warning_on_exceeded_aggregate_limit(self):
        '''
        Test that if the aggregate limit is exceeded.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-06-05',
            amounts=[20000],
            company=self.branch_a,
            accounts=[self.purchase_account]
        )
        line = move.invoice_line_ids[0]
        self.assertEqual(move.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line.l10n_in_line_warning, False)

        move_1 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-07-06',
            amounts=[20000],
            company=self.branch_b,
            accounts=[self.purchase_account]
        )
        line_1 = move_1.invoice_line_ids[0]
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_1.l10n_in_line_warning, False)

        move_2 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-08-06',
            amounts=[31000],
            company=self.branch_c,
            accounts=[self.purchase_account]
        )
        line_2 = move_2.invoice_line_ids[0]
        self.assertEqual(move_2.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")
        self.assertEqual(line_2.l10n_in_line_warning, True)

        move_3 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-09-06',
            amounts=[5000],
            company=self.branch_a,
            accounts=[self.purchase_account]
        )
        line_3 = move_3.invoice_line_ids[0]
        self.assertEqual(move_3.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_3.l10n_in_line_warning, False)

        move_4 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-10-07',
            amounts=[20000],
            company=self.branch_b,
            accounts=[self.purchase_account]
        )
        line_4 = move_4.invoice_line_ids[0]
        self.assertEqual(move_4.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_4.l10n_in_line_warning, False)

        move_5 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-11-08',
            amounts=[25000],
            company=self.branch_c,
            accounts=[self.purchase_account]
        )
        line_5 = move_5.invoice_line_ids[0]
        self.assertEqual(move_5.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")
        self.assertEqual(line_5.l10n_in_line_warning, True)

    def test_tcs_tds_warning_on_case_of_credit_note(self):
        '''
        Test that the aggregate limit in case of debit/credit note.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-09-01',
            amounts=[2000],
            company=self.branch_a,
            accounts=[self.internet_account]
        )
        line = move.invoice_line_ids[0]
        self.assertEqual(move.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line.l10n_in_line_warning, False)

        move_1 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-09-01',
            amounts=[3000],
            company=self.branch_a,
            accounts=[self.internet_account]
        )
        self.reverse_move(move, '2024-09-01')

        line_1 = move_1.invoice_line_ids[0]
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_1.l10n_in_line_warning, False)

        move_2 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-09-01',
            amounts=[2000],
            company=self.branch_a,
            accounts=[self.internet_account]
        )
        line_2 = move_2.invoice_line_ids[0]
        self.assertEqual(move_2.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_2.l10n_in_line_warning, False)

    def test_tcs_tds_warning_cleared_on_available_tax(self):
        '''
        Test when a tax is added to the move line with a similar tax group
        as the account.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[60000],
            taxes=[self.tax_194j],
            company=self.branch_a,
            accounts=[self.internet_account]
        )

        self.assertEqual(move.l10n_in_tcs_tds_warning, False)

    def test_tcs_tds_warning_for_multiple_accounts_in_lines(self):
        '''
        Test when there are multiple products in the move line and some of them
        have different accounts which have the different tax group as the account.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[1000, 6000, 5100000],
            company=self.branch_a,
            accounts=[self.internet_account, self.purchase_account, self.building_account],
            quantities=[10, 31, 1]
        )
        line_warning = [line.l10n_in_line_warning for line in move.invoice_line_ids]
        self.assertEqual(line_warning, [False, True, True])
        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C,  194IA on this transaction.")

        move_1 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[1000, 6000, 5100000],
            taxes=[self.tax_194j, self.tax_194c, self.tax_194ia],
            company=self.branch_a,
            accounts=[self.internet_account, self.purchase_account, self.building_account],
            quantities=[10, 31, 1]
        )
        line_warning = [line.l10n_in_line_warning for line in move_1.invoice_line_ids]
        self.assertEqual(line_warning, [False, False, False])
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, False)

    def test_tcs_tds_warning_for_if_line_has_price_zero(self):
        '''
        Test when any invoice line has Zero
        '''
        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[101000, 0],
            company=self.branch_a,
            accounts=[self.purchase_account, self.purchase_account],
        )
        line_warning = [line.l10n_in_line_warning for line in move.invoice_line_ids]
        self.assertEqual(line_warning, [True, False])
        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")

        move_1 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[0],
            company=self.branch_a,
            accounts=[self.purchase_account]
        )
        line = move_1.invoice_line_ids[0]
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line.l10n_in_line_warning, False)

    def test_tcs_tds_warning_for_all_lines_do_not_have_taxes(self):
        '''
        Test when there are multiple products in the move line and some of them
        don't have tax which has tax group same as chart of account they have in case
        of all line have same tcs/tds section.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[1000, 6000],
            taxes=[self.tax_194c],
            company=self.branch_a,
            accounts=[self.purchase_account, self.purchase_account],
            quantities=[15, 16]
        )

        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")

    def test_tcs_tds_warning_for_lines_with_mixed_accounts_and_taxes(self):
        '''
        Test when there are multiple products in the move line and some of them
        have different accounts and some of them don't have tax which have the same
        tax group as the account.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-01-01',
            amounts=[1000, 2000],
            taxes=[self.tax_194j],
            company=self.branch_a,
            accounts=[self.internet_account, self.purchase_account],
            quantities=[40, 80]
        )

        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")

    def test_tcs_tds_warning_for_company_branches(self):
        '''
        Test when the aggregate limit is exceeded in case of multiple branches
        of the company,the warning message should be set accordingly.
        '''

        self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-05-14',
            amounts=[25000],
            company=self.branch_a,
            accounts=[self.purchase_account]
        )

        self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-05-14',
            amounts=[25000],
            company=self.branch_b,
            accounts=[self.purchase_account]
        )

        self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-05-14',
            amounts=[25000],
            company=self.branch_c,
            accounts=[self.purchase_account],
            quantities=[25]
        )

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-05-14',
            amounts=[28000],
            company=self.branch_a,
            accounts=[self.purchase_account]
        )

        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")

    def test_tcs_tds_warning_tcs_use_in_bill(self):
        '''
        Test when tcs section is used in the bill creation.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-05-29',
            amounts=[1100000],
            company=self.branch_a,
            accounts=[self.sale_account]
        )
        line = move.invoice_line_ids[0]
        self.assertEqual(move.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line.l10n_in_line_warning, False)

    def test_tcs_tds_warning_tds_use_in_invoice(self):
        '''
        Test when tcs section is used in the bill creation.
        '''

        move = self.create_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            invoice_date='2024-05-29',
            amounts=[110000],
            company=self.branch_a,
            accounts=[self.purchase_account]
        )
        line = move.invoice_line_ids[0]
        self.assertEqual(move.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line.l10n_in_line_warning, False)

    def test_tcs_tds_warning_on_exceeded_aggregate_limit_some_invoice_has_tax(self):
        '''
        Test when the aggregate limit is exceeded when sone invoices
        have all nessecary taxes in its move lines.
        '''

        self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-09-01',
            amounts=[10000],
            company=self.branch_a,
            accounts=[self.internet_account]
        )

        self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-05-01',
            amounts=[25000],
            taxes=[self.tax_194j],
            company=self.branch_a,
            accounts=[self.internet_account]
        )

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-07-01',
            amounts=[10000],
            company=self.branch_a,
            accounts=[self.internet_account]
        )

        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194J on this transaction.")

    def test_tcs_tds_warning_all_type_of_invoice_same_account(self):
        '''
        Test when all type of invoices are created with the
        same chart of account.
        '''
        # bill
        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-09-01',
            amounts=[100000],
            company=self.branch_a,
            accounts=[self.purchase_account]
        )

        # debit note
        self.reverse_move(move, '2024-09-01')

        # invoice
        move_1 = self.create_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            invoice_date='2024-05-01',
            amounts=[250000],
            company=self.branch_a,
            accounts=[self.purchase_account]
        )

        # credit_note
        self.reverse_move(move_1, '2024-05-01')

        move_2 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-07-01',
            amounts=[10000],
            company=self.branch_a,
            accounts=[self.purchase_account]
        )
        self.assertEqual(move_2.l10n_in_tcs_tds_warning, False)

    def test_tcs_tds_warning_for_multiple_accounts_same_section_in_lines(self):
        '''
        Test when there are multiple products in the move line and some of them
        have different accounts which have the same tax group as the account.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[17000, 14000],
            company=self.branch_a,
            accounts=[self.house_expense_account, self.purchase_account],
        )
        line_warning = [line.l10n_in_line_warning for line in move.invoice_line_ids]
        self.assertEqual(line_warning, [True, True])
        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")

        move_1 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[17000, 13000],
            company=self.branch_a,
            accounts=[self.house_expense_account, self.purchase_account],
        )
        line_warning = [line.l10n_in_line_warning for line in move_1.invoice_line_ids]
        self.assertEqual(line_warning, [False, False])
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, False)

        move_2 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[30000],
            company=self.branch_a,
            accounts=[self.house_expense_account],
        )
        line_warning = [line.l10n_in_line_warning for line in move_2.invoice_line_ids]
        self.assertEqual(line_warning, [False])
        self.assertEqual(move_2.l10n_in_tcs_tds_warning, False)

        move_3 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[10000],
            company=self.branch_a,
            accounts=[self.purchase_account],
        )
        line_warning = [line.l10n_in_line_warning for line in move_3.invoice_line_ids]
        self.assertEqual(line_warning, [True])
        self.assertEqual(move_3.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")
