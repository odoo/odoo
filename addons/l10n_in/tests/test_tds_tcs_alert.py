from odoo import Command
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon
from odoo.tests import tagged, freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTdsTcsAlert(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ChartTemplate = cls.env['account.chart.template']
        if cls.env['ir.module.module']._get('l10n_in_pos').state == 'installed':
            cls.env.user.group_ids |= cls.env.ref("point_of_sale.group_pos_user")

        # ==== Chart of Accounts ====
        cls.purchase_account = ChartTemplate.ref('p2107')
        cls.purchase_account.write({
            'l10n_in_tds_tcs_section_id': cls.env.ref('l10n_in.tds_section_194c').id
        })
        cls.house_expense_account = ChartTemplate.ref('p2103')
        cls.house_expense_account.write({
            'l10n_in_tds_tcs_section_id': cls.env.ref('l10n_in.tds_section_194c').id
        })
        cls.internet_account = ChartTemplate.ref('p2105')
        cls.internet_account.write({
            'l10n_in_tds_tcs_section_id': cls.env.ref('l10n_in.tds_section_194j').id
        })
        cls.rent_account = ChartTemplate.ref('p2111')
        cls.rent_account.write({
            'l10n_in_tds_tcs_section_id': cls.env.ref('l10n_in.tds_section_194ib').id
        })
        cls.sale_account = ChartTemplate.ref('p20011')
        cls.sale_account.write({
            'l10n_in_tds_tcs_section_id': cls.env.ref('l10n_in.tcs_section_206c1g_r').id
        })
        cls.service_account = ChartTemplate.ref('p20021')
        cls.creditors_account = ChartTemplate.ref('p11211')

        # ==== Taxes ====
        cls.tax_194c = ChartTemplate.ref('tds_20_us_194c')
        cls.tax_194c.write({'l10n_in_section_id': cls.env.ref('l10n_in.tds_section_194c').id})
        cls.tax_194j = ChartTemplate.ref('tds_10_us_194j')
        cls.tax_194j.write({'l10n_in_section_id': cls.env.ref('l10n_in.tds_section_194j').id})
        cls.tax_194ib = ChartTemplate.ref('tds_20_us_194ib')
        cls.tax_194ib.write({'l10n_in_section_id': cls.env.ref('l10n_in.tds_section_194ib').id})
        cls.tax_206c1g_r = ChartTemplate.ref('tcs_5_us_206c_1g_som')
        cls.tax_206c1g_r.write({'l10n_in_section_id': cls.env.ref('l10n_in.tcs_section_206c1g_r').id})

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

    @classmethod
    def _create_invoice(cls, **invoice_args):
        # EXTEND 'account'
        invoice_args.setdefault('move_type', 'in_invoice')
        invoice_args.setdefault('post', True)
        return super()._create_invoice(**invoice_args)

    def tds_wizard_entry(self, move, lines):
        journal_id = self.env['account.journal'].search([('company_id', '=', self.env.company.id),('type', '=', 'general')], limit=1)
        for tax, amount in lines:
            self.env['l10n_in.withhold.wizard'].with_context(active_model='account.move', active_ids=move.ids).create({
                'journal_id': journal_id.id,
                'tax_id': tax.id,
                'base': amount,
                'date': move.invoice_date,
            }).action_create_and_post_withhold()

    def test_tcs_tds_warning(self):
        '''
        Test that if any of the limit is not exceeded.
        '''

        move = self._create_invoice_one_line(
            price_unit=29000,
            company_id=self.branch_a,
            account_id=self.internet_account,
        )

        self.assertEqual(move.l10n_in_warning, False)

    def test_tcs_tds_warning_on_exceeded_per_transaction_limit(self):
        '''
        Test that if the per transaction limit is exceeded.
        '''

        move = self._create_invoice_one_line(
            price_unit=31000,
            company_id=self.branch_a,
        )
        self.assertEqual(move.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 194C on this transaction.")

        move_1 = self._create_invoice_one_line(
            price_unit=31000,
            partner_id=self.partner_b,
            company_id=self.branch_b,
        )
        self.assertEqual(move_1.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 194C on this transaction.")

        self._create_invoice_one_line(
            price_unit=31000,
            partner_id=self.partner_b,
            company_id=self.branch_b,
        )

        move_3 = self._create_invoice_one_line(
            price_unit=31000,
            partner_id=self.partner_b,
            company_id=self.branch_b,
        )
        self.assertEqual(move_3.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 194C on this transaction.")

    def test_tcs_tds_warning_on_monthly_aggregate_limit(self):
        '''
        Test the monthly aggregate limit, the warning
        message should be set accordingly.
        '''

        with freeze_time('2024-06-05'):
            move = self._create_invoice_one_line(
                price_unit=30000,
                company_id=self.branch_a,
                account_id=self.rent_account,
            )
        self.assertEqual(move.l10n_in_warning, False)

        with freeze_time('2024-07-06'):
            move_1 = self._create_invoice_one_line(
                partner_id=self.partner_b,
                price_unit=20000,
                company_id=self.branch_b,
                account_id=self.rent_account,
            )
        self.assertEqual(move_1.l10n_in_warning, False)

        with freeze_time('2024-07-16'):
            move_2 = self._create_invoice_one_line(
                price_unit=31000,
                company_id=self.branch_c,
                account_id=self.rent_account,
            )
        self.assertEqual(move_2.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 194IB on this transaction.")

        with freeze_time('2024-09-06'):
            move_3 = self._create_invoice_one_line(
                price_unit=50000,
                company_id=self.branch_c,
                account_id=self.rent_account,
            )
        self.assertEqual(move_3.l10n_in_warning, False)

        with freeze_time('2024-09-16'):
            move_4 = self._create_invoice_one_line(
                price_unit=50000,
                company_id=self.branch_c,
                account_id=self.rent_account,
            )
        self.assertEqual(move_4.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 194IB on this transaction.")

    def test_tcs_tds_warning_partner_with_pan(self):
        '''
        Test the aggregate limit when partner don't have
        pan number and having pan number.
        '''
        # no pan number
        move = self._create_invoice_one_line(
            partner_id=self.partner_foreign,
            price_unit=30000,
            company_id=self.branch_a,
            account_id=self.internet_account,
        )
        self.assertEqual(move.l10n_in_warning, False)

        move_1 = self._create_invoice_one_line(
            partner_id=self.partner_foreign_2,
            price_unit=30000,
            company_id=self.branch_b,
            account_id=self.internet_account,
        )
        self.assertEqual(move_1.l10n_in_warning, False)

        # same pan number
        move_2 = self._create_invoice_one_line(
            price_unit=30000,
            company_id=self.branch_a,
            account_id=self.internet_account,
        )
        self.assertEqual(move_2.l10n_in_warning, False)

        move_3 = self._create_invoice_one_line(
            partner_id=self.partner_b,
            price_unit=30000,
            company_id=self.branch_b,
            account_id=self.internet_account,
        )
        self.assertEqual(move_3.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 194J on this transaction.")

    def test_tcs_tds_warning_on_exceeded_aggregate_limit(self):
        '''
        Test that if the aggregate limit is exceeded.
        '''
        with freeze_time('2024-06-05'):
            move = self._create_invoice_one_line(
                price_unit=20000,
                company_id=self.branch_a,
            )
        self.assertEqual(move.l10n_in_warning, False)

        with freeze_time('2024-07-06'):
            move_1 = self._create_invoice_one_line(
                partner_id=self.partner_b,
                price_unit=20000,
                company_id=self.branch_b,
            )
        self.assertEqual(move_1.l10n_in_warning, False)

        with freeze_time('2024-08-06'):
            move_2 = self._create_invoice_one_line(
                price_unit=31000,
                company_id=self.branch_c,
            )
        self.assertEqual(move_2.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 194C on this transaction.")

        with freeze_time('2024-09-06'):
            move_3 = self._create_invoice_one_line(
                partner_id=self.partner_b,
                price_unit=5000,
                company_id=self.branch_a,
            )
        self.assertEqual(move_3.l10n_in_warning, False)

        with freeze_time('2024-10-07'):
            move_4 = self._create_invoice_one_line(
                price_unit=20000,
                company_id=self.branch_b,
            )
        self.assertEqual(move_4.l10n_in_warning, False)

        with freeze_time('2024-11-08'):
            move_5 = self._create_invoice_one_line(
                partner_id=self.partner_b,
                price_unit=25000,
                company_id=self.branch_c,
            )
        self.assertEqual(move_5.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 194C on this transaction.")

    def test_tcs_tds_warning_on_case_of_credit_note(self):
        '''
        Test that the aggregate limit in case of debit/credit note.
        '''

        move = self._create_invoice_one_line(
            price_unit=2000,
            company_id=self.branch_a,
            account_id=self.internet_account
        )
        self.assertEqual(move.l10n_in_warning, False)

        move_1 = self._create_invoice_one_line(
            partner_id=self.partner_b,
            price_unit=3000,
            company_id=self.branch_a,
            account_id=self.internet_account
        )
        self._reverse_invoice(move, date='2024-09-01')

        self.assertEqual(move_1.l10n_in_warning, False)

        move_2 = self._create_invoice_one_line(
            price_unit=2000,
            company_id=self.branch_a,
            account_id=self.internet_account
        )
        self.assertEqual(move_2.l10n_in_warning, False)

    def test_tcs_tds_warning_cleared_on_available_tax(self):
        '''
        Test when a tax is added to the move line with a similar tax group
        as the account.
        '''

        move = self._create_invoice_one_line(
            move_type='out_invoice',
            price_unit=710000,
            tax_ids=self.tax_206c1g_r,
            company_id=self.branch_a,
        )

        self.assertEqual(move.l10n_in_warning, False)

    def test_tcs_tds_warning_for_multiple_accounts_in_lines(self):
        '''
        Test when there are multiple products in the move line and some of them
        have different accounts which have the different tax group as the account.
        '''

        move = self._create_invoice(
            company_id=self.branch_a,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100000, quantity=15, account_id=self.rent_account),
                self._prepare_invoice_line(price_unit=1100000, quantity=16, account_id=self.internet_account),
                self._prepare_invoice_line(price_unit=710000, quantity=10, account_id=self.purchase_account),
            ],
        )
        self.assertTrue(move.l10n_in_warning)

        move_1 = self._create_invoice(
            company_id=self.branch_a,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100000, quantity=15, account_id=self.rent_account),
                self._prepare_invoice_line(price_unit=1100000, quantity=16, account_id=self.internet_account),
                self._prepare_invoice_line(price_unit=710000, quantity=10, account_id=self.purchase_account),
            ],
        )
        self.tds_wizard_entry(move=move_1, lines=[(self.tax_194ib, 100000), (self.tax_194j, 100000), (self.tax_194c, 100000)])
        move_1.button_draft()
        move_1.action_post()
        self.assertEqual(move_1.l10n_in_warning, False)

    def test_tcs_tds_warning_for_if_line_has_price_zero(self):
        '''
        Test when any invoice line has Zero
        '''
        move = self._create_invoice(
            company_id=self.branch_a,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=101000),
                self._prepare_invoice_line(price_unit=0),
            ],
        )
        self.assertEqual(move.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 194C on this transaction.")

        move_1 = self._create_invoice_one_line(
            price_unit=0,
            company_id=self.branch_a,
        )
        self.assertEqual(move_1.l10n_in_warning, False)

    def test_tcs_tds_warning_for_all_lines_do_not_have_taxes(self):
        '''
        Test when tds entry created and warning will removed
        '''
        move = self._create_invoice(
            company_id=self.branch_a,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=1000, quantity=15),
                self._prepare_invoice_line(price_unit=6000, quantity=16),
            ],
        )
        self.assertEqual(move.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 194C on this transaction.")
        self.tds_wizard_entry(move=move, lines=[(self.tax_194c, 100000)])
        move.line_ids.remove_move_reconcile()
        self.assertEqual(move.l10n_in_warning, False)

    def test_tcs_tds_warning_for_company_branches(self):
        '''
        Test when the aggregate limit is exceeded in case of multiple branches
        of the company,the warning message should be set accordingly.
        '''

        self._create_invoice_one_line(
            price_unit=25000,
            company_id=self.branch_a,
        )
        self._create_invoice_one_line(
            partner_id=self.partner_b,
            price_unit=25000,
            company_id=self.branch_b,
        )
        self._create_invoice_one_line(
            partner_id=self.partner_b,
            price_unit=25000,
            company_id=self.branch_c,
            quantity=25
        )
        move = self._create_invoice_one_line(
            price_unit=28000,
            company_id=self.branch_a,
        )

        self.assertEqual(move.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 194C on this transaction.")

    def test_tcs_tds_warning_tcs_use_in_bill(self):
        '''
        Test when tcs section is used in the bill creation.
        '''

        move = self._create_invoice_one_line(
            price_unit=1100000,
            company_id=self.branch_a,
            account_id=self.sale_account
        )
        self.assertEqual(move.l10n_in_warning, False)

    def test_tcs_tds_warning_tds_use_in_invoice(self):
        '''
        Test when tcs section is used in the bill creation.
        '''

        move = self._create_invoice_one_line(
            move_type='out_invoice',
            price_unit=110000,
            company_id=self.branch_a,
        )
        self.assertEqual(move.l10n_in_warning, False)

    def test_tcs_tds_warning_for_multiple_accounts_same_section_in_lines(self):
        '''
        Test when there are multiple products in the move line and some of them
        have different accounts which have the same tax group as the account.
        '''

        move = self._create_invoice(
            company_id=self.branch_a,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=17000, account_id=self.house_expense_account),
                self._prepare_invoice_line(price_unit=14000, account_id=self.purchase_account),
            ],
        )
        self.assertEqual(move.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 194C on this transaction.")

        move_1 = self._create_invoice(
            company_id=self.branch_a,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=17000, account_id=self.house_expense_account),
                self._prepare_invoice_line(price_unit=13000, account_id=self.purchase_account),
            ],
        )
        self.assertEqual(move_1.l10n_in_warning, False)

        move_2 = self._create_invoice_one_line(
            price_unit=30000,
            company_id=self.branch_a,
            account_id=self.house_expense_account,
        )
        self.assertEqual(move_2.l10n_in_warning, False)

        move_3 = self._create_invoice_one_line(
            price_unit=10000,
            company_id=self.branch_a,
        )
        self.assertEqual(move_3.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 194C on this transaction.")

    def test_tcs_tds_warning_for_not_consider_draft_cancel_invoices_for_aggregate(self):
        '''
        Test to exclude draft and canceled invoices from aggregate
        total calculation.
        '''

        move = self._create_invoice_one_line(
            price_unit=16000,
            company_id=self.branch_a,
            account_id=self.purchase_account,
        )
        move.button_cancel()
        self.assertEqual(move.l10n_in_warning, False)

        move_1 = self._create_invoice_one_line(
            price_unit=25000,
            company_id=self.branch_a,
            account_id=self.purchase_account,
        )
        self.assertEqual(move_1.l10n_in_warning, False)

        move_2 = self._create_invoice_one_line(
            price_unit=85000,
            company_id=self.branch_a,
            account_id=self.purchase_account,
        )
        self.assertEqual(move_2.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to deduct TDS u/s 194C on this transaction.")

    def test_tcs_tds_warning_if_some_lines_has_tax(self):
        '''
        Test when a tax is added to the some of the move line
        '''

        move = self._create_invoice(
            move_type='out_invoice',
            company_id=self.branch_a,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=710000, tax_ids=self.tax_206c1g_r),
                self._prepare_invoice_line(price_unit=710000),
            ],
        )

        self.assertEqual(move.l10n_in_warning['tds_tcs_threshold_alert']['message'], "It's advisable to collect TCS u/s 206C(1G) Remittance on this transaction.")
