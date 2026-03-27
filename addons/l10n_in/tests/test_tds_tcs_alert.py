from odoo import Command
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTdsTcsAlert(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ChartTemplate = cls.env['account.chart.template']

        # ==== Chart of Accounts ====
        cls.purchase_account = ChartTemplate.ref('p2107')
        cls.purchase_account.write({
            'l10n_in_tds_tcs_section_id': cls.env.ref('l10n_in.tds_section_393_1_6_i_a_contr_ind_huf').id
        })
        cls.house_expense_account = ChartTemplate.ref('p2103')
        cls.house_expense_account.write({
            'l10n_in_tds_tcs_section_id': cls.env.ref('l10n_in.tds_section_393_1_6_i_a_contr_ind_huf').id
        })
        cls.internet_account = ChartTemplate.ref('p2105')
        cls.internet_account.write({
            'l10n_in_tds_tcs_section_id': cls.env.ref('l10n_in.tds_section_393_1_6_iii_b_prof').id
        })
        cls.rent_account = ChartTemplate.ref('p2111')
        cls.rent_account.write({
            'l10n_in_tds_tcs_section_id': cls.env.ref('l10n_in.tds_section_393_1_2_ii_b_rent_land').id
        })
        cls.sale_account = ChartTemplate.ref('p20011')
        cls.sale_account.write({
            'l10n_in_tds_tcs_section_id': cls.env.ref('l10n_in.tcs_section_394_1_7_b_lrs_oth').id
        })
        cls.service_account = ChartTemplate.ref('p20021')
        cls.creditors_account = ChartTemplate.ref('p11211')

        # ==== Taxes ====
        cls.tax_393_1_6_i_a = ChartTemplate.ref('tds_sale_1_us_393_1_6_i_a')
        cls.tax_393_1_6_iii_b = ChartTemplate.ref('tds_sale_10_us_393_1_6_iii_b')
        cls.tax_393_1_2_ii_b = ChartTemplate.ref('tds_sale_10_us_393_1_2_ii_b')
        cls.tax_394_1_7_b = ChartTemplate.ref('tcs_20_us_394_1_7_b_lrs_oth')

        country_in_id = cls.env.ref("base.in").id

        cls.partner_b.write({
            'vat': '27ABCPM8965E1ZE',
        })
        cls.partner_foreign_2 = cls.partner_foreign.copy()

        # ==== Company ====
        cls.env.company.write({
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

    def create_invoice(self, move_type=None, partner=None, invoice_date=None, amounts=None, taxes=[], company=None, accounts=[], quantities=[]):
        invoice = self.init_invoice(
            move_type=move_type or 'in_invoice',
            partner=partner,
            invoice_date=invoice_date,
            post=False,
            amounts=amounts,
            company=company
        )

        for i, account in enumerate(accounts):
            invoice.invoice_line_ids[i].account_id = account

        for i, quantity in enumerate(quantities):
            invoice.invoice_line_ids[i].quantity = quantity

        for i, tax in enumerate(taxes):
            invoice.invoice_line_ids[i].tax_ids = tax
        invoice.action_post()
        return invoice

    def tds_wizard_entry(self, move, lines):
        journal_id = self.env['account.journal'].search([('company_id', '=', self.env.company.id),('type', '=', 'general')], limit=1)
        for tax, amount in lines:
            self.env['l10n_in.withhold.wizard'].with_context(active_model='account.move', active_ids=move.ids).create({
                'journal_id': journal_id.id,
                'tax_id': tax.id,
                'base': amount,
                'date': move.invoice_date,
            }).action_create_and_post_withhold()

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

        self.assertFalse(move.l10n_in_warning)

    def test_tcs_tds_warning_on_exceeded_per_transaction_limit(self):
        '''
        Test that if the per transaction limit is exceeded.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-06-05',
            amounts=[31000],
            company=self.branch_a,
            quantities=[1]
        )
        self.assertEqual(move.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 393(1)6(i)(a) CONTR IND/HUF on this transaction.")

        move_1 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-06-05',
            amounts=[31000],
            company=self.branch_b,
            quantities=[1]
        )
        self.assertEqual(move_1.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 393(1)6(i)(a) CONTR IND/HUF on this transaction.")

        move_3 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-06-05',
            amounts=[15000],
            company=self.branch_b,
            quantities=[1]
        )
        self.assertFalse(move_3.l10n_in_warning)

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
        self.assertFalse(move.l10n_in_warning)

        move_1 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-07-06',
            amounts=[20000],
            company=self.branch_b,
            accounts=[self.rent_account]
        )
        self.assertFalse(move_1.l10n_in_warning)

        move_2 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-07-16',
            amounts=[31000],
            company=self.branch_c,
            accounts=[self.rent_account]
        )
        self.assertEqual(move_2.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 393(1)2(ii)(b) RENT LAND on this transaction.")

        move_3 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-09-06',
            amounts=[50000],
            company=self.branch_c,
            accounts=[self.rent_account]
        )
        self.assertFalse(move_3.l10n_in_warning)

        move_4 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-09-16',
            amounts=[50000],
            company=self.branch_c,
            accounts=[self.rent_account]
        )
        self.assertEqual(move_4.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 393(1)2(ii)(b) RENT LAND on this transaction.")

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
        self.assertFalse(move.l10n_in_warning)

        move_1 = self.create_invoice(
            partner=self.partner_foreign_2,
            invoice_date='2024-06-05',
            amounts=[30000],
            company=self.branch_b,
            accounts=[self.internet_account]
        )
        self.assertFalse(move_1.l10n_in_warning)

        # same pan number
        move_2 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-06-05',
            amounts=[30000],
            company=self.branch_a,
            accounts=[self.internet_account]
        )
        self.assertFalse(move_2.l10n_in_warning)

        move_3 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-06-05',
            amounts=[30000],
            company=self.branch_b,
            accounts=[self.internet_account]
        )
        self.assertEqual(move_3.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 393(1)6(iii)(b) PROF on this transaction.")

    def test_tcs_tds_warning_on_exceeded_aggregate_limit(self):
        '''
        Test that if the aggregate limit is exceeded.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-06-05',
            amounts=[20000],
            company=self.branch_a,
        )
        self.assertFalse(move.l10n_in_warning)

        move_1 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-07-06',
            amounts=[20000],
            company=self.branch_b,
        )
        self.assertFalse(move_1.l10n_in_warning)
        move_2 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-08-06',
            amounts=[31000],
            company=self.branch_c,
        )
        self.assertEqual(move_2.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 393(1)6(i)(a) CONTR IND/HUF on this transaction.")

        move_3 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-09-06',
            amounts=[5000],
            company=self.branch_a,
        )
        self.assertFalse(move_3.l10n_in_warning)

        move_4 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-10-07',
            amounts=[20000],
            company=self.branch_b,
        )
        self.assertFalse(move_4.l10n_in_warning)

        move_5 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-11-08',
            amounts=[25000],
            company=self.branch_c,
        )
        self.assertEqual(move_5.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 393(1)6(i)(a) CONTR IND/HUF on this transaction.")

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
        self.assertFalse(move.l10n_in_warning)

        move_1 = self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-09-01',
            amounts=[3000],
            company=self.branch_a,
            accounts=[self.internet_account]
        )
        self.reverse_move(move, '2024-09-01')

        self.assertFalse(move_1.l10n_in_warning)

        move_2 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-09-01',
            amounts=[2000],
            company=self.branch_a,
            accounts=[self.internet_account]
        )
        self.assertFalse(move_2.l10n_in_warning)

    def test_tcs_tds_warning_cleared_on_available_tax(self):
        '''
        Test when a tax is added to the move line with a similar tax group
        as the account.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            move_type='out_invoice',
            invoice_date='2022-12-12',
            amounts=[710000],
            taxes=[self.tax_394_1_7_b],
            company=self.branch_a,
        )

        self.assertFalse(move.l10n_in_warning)

    def test_tcs_tds_warning_for_multiple_accounts_in_lines(self):
        '''
        Test when there are multiple products in the move line and some of them
        have different accounts which have the different tax group as the account.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            move_type='in_invoice',
            invoice_date='2022-12-12',
            amounts=[100000, 1100000, 710000],
            company=self.branch_a,
            accounts=[self.rent_account, self.internet_account, self.purchase_account],
            quantities=[15, 16, 10]
        )
        self.assertTrue(move.l10n_in_warning)

        move_1 = self.create_invoice(
            partner=self.partner_a,
            move_type='in_invoice',
            invoice_date='2022-12-12',
            amounts=[1000000.0, 1100000.0, 710000],
            company=self.branch_a,
            accounts=[self.rent_account, self.internet_account, self.purchase_account],
        )
        self.tds_wizard_entry(move=move_1, lines=[(self.tax_393_1_2_ii_b, 100000), (self.tax_393_1_6_iii_b, 100000), (self.tax_393_1_6_i_a, 100000)])
        move_1.button_draft()
        move_1.action_post()
        self.assertFalse(move_1.l10n_in_warning)

    def test_tcs_tds_warning_for_if_line_has_price_zero(self):
        '''
        Test when any invoice line has Zero
        '''
        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[101000, 0],
            company=self.branch_a,
        )
        self.assertEqual(move.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 393(1)6(i)(a) CONTR IND/HUF on this transaction.")

        move_1 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[0],
            company=self.branch_a,
        )
        self.assertFalse(move_1.l10n_in_warning)

    def test_tcs_tds_warning_for_all_lines_do_not_have_taxes(self):
        '''
        Test when tds entry created and warning will removed
        '''
        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[1000, 6000],
            company=self.branch_a,
            accounts=[],
            quantities=[15, 16]
        )
        self.assertEqual(move.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 393(1)6(i)(a) CONTR IND/HUF on this transaction.")
        self.tds_wizard_entry(move=move, lines=[(self.tax_393_1_6_i_a, 100000)])
        move.line_ids.remove_move_reconcile()
        self.assertFalse(move.l10n_in_warning)

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
        )

        self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-05-14',
            amounts=[25000],
            company=self.branch_b,
        )

        self.create_invoice(
            partner=self.partner_b,
            invoice_date='2024-05-14',
            amounts=[25000],
            company=self.branch_c,
            quantities=[25]
        )

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-05-14',
            amounts=[28000],
            company=self.branch_a,
        )

        self.assertEqual(move.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 393(1)6(i)(a) CONTR IND/HUF on this transaction.")

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
        self.assertFalse(move.l10n_in_warning)

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
        )
        self.assertFalse(move.l10n_in_warning)

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
        self.assertEqual(move.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 393(1)6(i)(a) CONTR IND/HUF on this transaction.")

        move_1 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[17000, 13000],
            company=self.branch_a,
            accounts=[self.house_expense_account, self.purchase_account],
        )
        self.assertFalse(move_1.l10n_in_warning)

        move_2 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[30000],
            company=self.branch_a,
            accounts=[self.house_expense_account],
        )
        self.assertFalse(move_2.l10n_in_warning)

        move_3 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[10000],
            company=self.branch_a,
        )
        self.assertEqual(move_3.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 393(1)6(i)(a) CONTR IND/HUF on this transaction.")

    def test_tcs_tds_warning_for_not_consider_draft_cancel_invoices_for_aggregate(self):
        '''
        Test to exclude draft and canceled invoices from aggregate
        total calculation.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[16000],
            company=self.branch_a,
            accounts=[self.purchase_account],
        )
        move.button_cancel()
        self.assertFalse(move.l10n_in_warning)

        move_1 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[25000],
            company=self.branch_a,
            accounts=[self.purchase_account],
        )
        self.assertFalse(move_1.l10n_in_warning)

        move_2 = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[85000],
            company=self.branch_a,
            accounts=[self.purchase_account],
        )
        self.assertEqual(move_2.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 393(1)6(i)(a) CONTR IND/HUF on this transaction.")

    def test_tcs_tds_warning_if_some_lines_has_tax(self):
        '''
        Test when a tax is added to the some of the move line
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            move_type='out_invoice',
            invoice_date='2022-12-12',
            amounts=[710000, 710000],
            taxes=[self.tax_394_1_7_b],
            company=self.branch_a,
        )

        self.assertEqual(move.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to collect TCS u/s TCS 394(1)7(b) Remittance (Other) on this transaction.")
