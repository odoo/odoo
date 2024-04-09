from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestTdsTcsAlert(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('in')
    def setUpClass(cls):
        super().setUpClass()
        # ==== Tax Groups ====
        # per transection = 30000 and aggregate = 100000 and period = year and unit = total
        cls.tds_194c = cls.env['account.chart.template'].ref('tds_group_194c')
        # per transection = False and aggregate = 30000 and period = year and unit = total
        cls.tds_194j = cls.env['account.chart.template'].ref('tds_group_194j')
        # per transection = False and aggregate = 240000 and period = year and unit = total
        cls.tds_194i = cls.env['account.chart.template'].ref('tds_group_194i')
        # per transection = False and aggregate = 50000 and period = month and unit = total
        cls.tds_194ib = cls.env['account.chart.template'].ref('tds_group_194ib')
        # per transection = 5000000 and aggregate = False and period = year and unit = per_unit
        cls.tds_194ia = cls.env['account.chart.template'].ref('tds_group_194ia')
        # per transection = False and aggregate = 700000 and period = year and unit = total
        cls.tcs_206c1g_r = cls.env['account.chart.template'].ref('tcs_group_206c1g_r')
        # per transection = 1000000 and aggregate = false and period = year and unit = per_unit
        cls.tcs_206c1f_mv = cls.env['account.chart.template'].ref('tcs_group_206c1f_mv')

        # ==== Chart of Accounts ====
        cls.purchase_account = cls.env['account.chart.template'].ref('p2107')
        cls.purchase_account.write({
            'l10n_in_tds_tcs_section': cls.tds_194c.id
        })
        cls.internet_account = cls.env['account.chart.template'].ref('p2105')
        cls.internet_account.write({
            'l10n_in_tds_tcs_section': cls.tds_194j.id
        })
        cls.business_account = cls.env['account.chart.template'].ref('p2110')
        cls.business_account.write({
            'l10n_in_tds_tcs_section': cls.tds_194i.id
        })
        cls.rent_account = cls.env['account.chart.template'].ref('p2111')
        cls.rent_account.write({
            'l10n_in_tds_tcs_section': cls.tds_194ib.id
        })
        cls.building_account = cls.env['account.chart.template'].ref('p1011')
        cls.building_account.write({
            'l10n_in_tds_tcs_section': cls.tds_194ia.id
        })
        cls.sale_account = cls.env['account.chart.template'].ref('p20011')
        cls.sale_account.write({
            'l10n_in_tds_tcs_section': cls.tcs_206c1g_r.id
        })
        cls.service_account = cls.env['account.chart.template'].ref('p20021')
        cls.service_account.write({
            'l10n_in_tds_tcs_section': cls.tcs_206c1f_mv.id
        })
        cls.creditors_account = cls.env['account.chart.template'].ref('p11211')

        # ==== Taxes ====
        cls.tax_194c = cls.env['account.chart.template'].ref('tds_20_us_194c')
        cls.tax_194j = cls.env['account.chart.template'].ref('tds_10_us_194j')
        cls.tax_194i = cls.env['account.chart.template'].ref('tds_20_us_194i')
        cls.tax_194ia = cls.env['account.chart.template'].ref('tds_20_us_194ia')
        cls.tax_194ib = cls.env['account.chart.template'].ref('tds_20_us_194ib')
        cls.tax_206c1g_r = cls.env['account.chart.template'].ref('tcs_5_us_206c_1g_som')
        cls.tax_206c1f_mv = cls.env['account.chart.template'].ref('tcs_1_us_206c_1f_mv')

        country_in_id = cls.env.ref("base.in").id

        # ==== Partners ====
        cls.partner_a.write({
            'vat': '27DJMPM8965E1ZE',
            'l10n_in_pan': 'DJMPM8965E',
            'l10n_in_gst_treatment': 'regular',
            'state_id': cls.env.ref("base.state_in_mh"),
            'country_id': country_in_id,
        })
        cls.partner_b.write({
            'vat': '24DJMPM8965E1ZE',
            'l10n_in_pan': 'DJMPM8965E',
            'l10n_in_gst_treatment': 'composition',
            'state_id': cls.env.ref("base.state_in_gj"),
            'country_id': country_in_id,
        })
        cls.partner_c = cls.env['res.partner'].create({
            'name': "Overseas partner",
            'l10n_in_gst_treatment': 'overseas',
            'state_id': cls.env.ref("base.state_us_1").id,
            'country_id': cls.env.ref("base.us").id,
            'zip': "123456",
        })
        cls.partner_d = cls.partner_c.copy()

        # ==== Company ====
        cls.company_data["company"].write({
            "vat": "24AAGCC7144L6ZJ",
            "state_id": cls.env.ref("base.state_in_gj").id,
            "street": "street1",
            "city": "city1",
            "zip": "123456",
            "country_id": country_in_id,
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

    def create_invoice(self, move_type=None, partner=None, invoice_date=None, post=False, amounts=None, taxes=None, company=None, accounts=None, quantities=None):
        invoice = self.init_invoice(
            move_type=move_type,
            partner=partner,
            invoice_date=invoice_date,
            post=False,
            amounts=amounts,
            company=company
        )

        for i, account in enumerate(accounts):
            invoice.invoice_line_ids[i].account_id = account.id

        for i, quantity in enumerate(quantities):
            invoice.invoice_line_ids[i].quantity = quantity

        if taxes:
            for i, tax in enumerate(taxes):
                invoice.invoice_line_ids[i].tax_ids = tax.ids

        if post:
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
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-06-05',
            post=True,
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
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-06-05',
            post=True,
            amounts=[31000],
            company=self.branch_a,
            accounts=[self.purchase_account],
            quantities=[1]
        )
        line = move.invoice_line_ids[0]
        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")
        self.assertEqual(line.l10n_in_line_warning, True)

        move_1 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_b,
            invoice_date='2024-06-05',
            post=True,
            amounts=[31000],
            company=self.branch_b,
            accounts=[self.purchase_account],
            quantities=[1]
        )
        line_1 = move_1.invoice_line_ids[0]
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")
        self.assertEqual(line_1.l10n_in_line_warning, True)

        move_2 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_b,
            invoice_date='2024-06-05',
            post=True,
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
            move_type='in_invoice',
            partner=self.partner_b,
            invoice_date='2024-06-05',
            post=True,
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
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-06-05',
            post=True,
            amounts=[30000],
            company=self.branch_a,
            accounts=[self.rent_account],
            quantities=[1]
        )
        line = move.invoice_line_ids[0]
        self.assertEqual(move.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line.l10n_in_line_warning, False)

        move_1 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_b,
            invoice_date='2024-07-06',
            post=True,
            amounts=[20000],
            company=self.branch_b,
            accounts=[self.rent_account],
            quantities=[1]
        )
        line_1 = move_1.invoice_line_ids[0]
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_1.l10n_in_line_warning, False)

        move_2 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-07-16',
            post=True,
            amounts=[31000],
            company=self.branch_c,
            accounts=[self.rent_account],
            quantities=[1]
        )
        line_2 = move_2.invoice_line_ids[0]
        self.assertEqual(move_2.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194IB on this transaction.")
        self.assertEqual(line_2.l10n_in_line_warning, True)

        move_3 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-09-06',
            post=True,
            amounts=[50000],
            company=self.branch_c,
            accounts=[self.rent_account],
            quantities=[1]
        )
        line_3 = move_3.invoice_line_ids[0]
        self.assertEqual(move_3.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_3.l10n_in_line_warning, False)

        move_4 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-09-16',
            post=True,
            amounts=[50000],
            taxes=[self.tax_194ib],
            company=self.branch_c,
            accounts=[self.rent_account],
            quantities=[1]
        )
        line_4 = move_4.invoice_line_ids[0]
        self.assertEqual(move_4.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_4.l10n_in_line_warning, False)

        move_5 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-05-16',
            post=True,
            amounts=[50000],
            taxes=[self.tax_194ib],
            company=self.branch_c,
            accounts=[self.rent_account],
            quantities=[1]
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
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-06-05',
            post=True,
            amounts=[6000000, 2600000, 5200000, 300000],
            company=self.branch_a,
            accounts=[self.building_account, self.building_account, self.building_account, self.building_account],
            quantities=[2, 2, 1, 1]
        )
        line = move.invoice_line_ids[0]
        line_1 = move.invoice_line_ids[1]
        line_2 = move.invoice_line_ids[2]
        line_3 = move.invoice_line_ids[3]

        self.assertEqual(line.l10n_in_line_warning, True)
        self.assertEqual(line_1.l10n_in_line_warning, False)
        self.assertEqual(line_2.l10n_in_line_warning, True)
        self.assertEqual(line_3.l10n_in_line_warning, False)
        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194IA on this transaction.")

        move_1 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-06-05',
            post=True,
            amounts=[6000000, 2600000, 5200000, 300000],
            taxes=[self.tax_194ia, self.tax_194ia, self.tax_194ia, self.tax_194ia],
            company=self.branch_a,
            accounts=[self.building_account, self.building_account, self.building_account, self.building_account],
            quantities=[2, 2, 1, 1]
        )
        line = move_1.invoice_line_ids[0]
        line_1 = move_1.invoice_line_ids[1]
        line_2 = move_1.invoice_line_ids[2]
        line_3 = move_1.invoice_line_ids[3]

        self.assertEqual(line.l10n_in_line_warning, False)
        self.assertEqual(line_1.l10n_in_line_warning, False)
        self.assertEqual(line_2.l10n_in_line_warning, False)
        self.assertEqual(line_3.l10n_in_line_warning, False)
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, False)

    def test_tcs_tds_warning_partner_wiht_pan(self):
        '''
        Test the aggregate limit when partner don't have
        pan number and having pan number.
        '''
        # no pan number
        move = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_c,
            invoice_date='2024-06-05',
            post=True,
            amounts=[1000],
            company=self.branch_a,
            accounts=[self.internet_account],
            quantities=[30]
        )
        line = move.invoice_line_ids[0]
        self.assertEqual(move.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line.l10n_in_line_warning, False)

        move_1 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_d,
            invoice_date='2024-06-05',
            post=True,
            amounts=[1000],
            company=self.branch_b,
            accounts=[self.internet_account],
            quantities=[30]
        )
        line_1 = move_1.invoice_line_ids[0]
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_1.l10n_in_line_warning, False)

        # same pan number
        move_2 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-06-05',
            post=True,
            amounts=[1000],
            company=self.branch_a,
            accounts=[self.internet_account],
            quantities=[30]
        )
        line_2 = move_2.invoice_line_ids[0]
        self.assertEqual(move_2.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_2.l10n_in_line_warning, False)

        move_3 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_b,
            invoice_date='2024-06-05',
            post=True,
            amounts=[1000],
            company=self.branch_b,
            accounts=[self.internet_account],
            quantities=[30]
        )
        line_3 = move_3.invoice_line_ids[0]
        self.assertEqual(move_3.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194J on this transaction.")
        self.assertEqual(line_3.l10n_in_line_warning, True)

    def test_tcs_tds_warning_on_exceeded_aggregate_limit(self):
        '''
        Test that if the aggregate limit is exceeded.
        '''

        move = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-06-05',
            post=True,
            amounts=[1000],
            company=self.branch_a,
            accounts=[self.purchase_account],
            quantities=[20]
        )
        line = move.invoice_line_ids[0]
        self.assertEqual(move.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line.l10n_in_line_warning, False)

        move_1 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_b,
            invoice_date='2024-07-06',
            post=True,
            amounts=[1000],
            company=self.branch_b,
            accounts=[self.purchase_account],
            quantities=[20]
        )
        line_1 = move_1.invoice_line_ids[0]
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_1.l10n_in_line_warning, False)

        move_2 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-08-06',
            post=True,
            amounts=[1000],
            company=self.branch_c,
            accounts=[self.purchase_account],
            quantities=[31]
        )
        line_2 = move_2.invoice_line_ids[0]
        self.assertEqual(move_2.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")
        self.assertEqual(line_2.l10n_in_line_warning, True)

        move_3 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_b,
            invoice_date='2024-09-06',
            post=True,
            amounts=[1000],
            company=self.branch_a,
            accounts=[self.purchase_account],
            quantities=[5]
        )
        line_3 = move_3.invoice_line_ids[0]
        self.assertEqual(move_3.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_3.l10n_in_line_warning, False)

        move_4 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-10-07',
            post=True,
            amounts=[1000],
            company=self.branch_b,
            accounts=[self.purchase_account],
            quantities=[20]
        )
        line_4 = move_4.invoice_line_ids[0]
        self.assertEqual(move_4.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_4.l10n_in_line_warning, False)

        move_5 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_b,
            invoice_date='2024-11-08',
            post=True,
            amounts=[1000],
            company=self.branch_c,
            accounts=[self.purchase_account],
            quantities=[25]
        )
        line_5 = move_5.invoice_line_ids[0]
        self.assertEqual(move_5.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")
        self.assertEqual(line_5.l10n_in_line_warning, True)

    def test_tcs_tds_warning_on_case_of_credit_note(self):
        '''
        Test that the aggregate limit in case of debit/credit note.
        '''

        move = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-09-01',
            post=True,
            amounts=[200],
            company=self.branch_a,
            accounts=[self.internet_account],
            quantities=[10]
        )
        line = move.invoice_line_ids[0]
        self.assertEqual(move.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line.l10n_in_line_warning, False)

        move_1 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_b,
            invoice_date='2024-09-01',
            post=True,
            amounts=[300],
            company=self.branch_a,
            accounts=[self.internet_account],
            quantities=[10]
        )
        self.reverse_move(move, '2024-09-01')

        line_1 = move_1.invoice_line_ids[0]
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line_1.l10n_in_line_warning, False)

        move_2 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-09-01',
            post=True,
            amounts=[200],
            company=self.branch_a,
            accounts=[self.internet_account],
            quantities=[10]
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
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2022-12-12',
            post=True,
            amounts=[1000],
            taxes=[self.tax_194j],
            company=self.branch_a,
            accounts=[self.internet_account],
            quantities=[60]
        )

        self.assertEqual(move.l10n_in_tcs_tds_warning, False)

    def test_tcs_tds_warning_for_multiple_accounts_in_lines(self):
        '''
        Test when there are multiple products in the move line and some of them
        have different accounts which have the different tax group as the account.
        '''

        move = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2022-12-12',
            post=True,
            amounts=[1000, 6000, 5100000],
            company=self.branch_a,
            accounts=[self.internet_account, self.purchase_account, self.building_account],
            quantities=[10, 31, 1]
        )
        line = move.invoice_line_ids[0]
        line_1 = move.invoice_line_ids[1]
        line_2 = move.invoice_line_ids[2]
        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C,  194IA on this transaction.")
        self.assertEqual(line.l10n_in_line_warning, False)
        self.assertEqual(line_1.l10n_in_line_warning, True)
        self.assertEqual(line_2.l10n_in_line_warning, True)

        move_1 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2022-12-12',
            post=True,
            amounts=[1000, 6000, 5100000],
            taxes=[self.tax_194j, self.tax_194c, self.tax_194ia],
            company=self.branch_a,
            accounts=[self.internet_account, self.purchase_account, self.building_account],
            quantities=[10, 31, 1]
        )
        line = move_1.invoice_line_ids[0]
        line_1 = move_1.invoice_line_ids[1]
        line_2 = move_1.invoice_line_ids[2]
        self.assertEqual(move_1.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line.l10n_in_line_warning, False)
        self.assertEqual(line_1.l10n_in_line_warning, False)
        self.assertEqual(line_2.l10n_in_line_warning, False)

    def test_tcs_tds_warning_for_if_line_has_price_zero(self):
        '''
        Test when any invoice line has Zero
        '''
        move = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2022-12-12',
            post=True,
            amounts=[1000, 0],
            company=self.branch_a,
            accounts=[self.purchase_account, self.purchase_account],
            quantities=[101, 1]
        )
        line = move.invoice_line_ids[0]
        line_1 = move.invoice_line_ids[1]
        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")
        self.assertEqual(line.l10n_in_line_warning, True)
        self.assertEqual(line_1.l10n_in_line_warning, False)

        move_1 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2022-12-12',
            post=True,
            amounts=[0],
            company=self.branch_a,
            accounts=[self.purchase_account],
            quantities=[0]
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
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2022-12-12',
            post=True,
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
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-01-01',
            post=True,
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
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-05-14',
            post=True,
            amounts=[1000],
            company=self.branch_a,
            accounts=[self.purchase_account],
            quantities=[25]
        )

        self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_b,
            invoice_date='2024-05-14',
            post=True,
            amounts=[1000],
            company=self.branch_b,
            accounts=[self.purchase_account],
            quantities=[25]
        )

        self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_b,
            invoice_date='2024-05-14',
            post=True,
            amounts=[1000],
            company=self.branch_c,
            accounts=[self.purchase_account],
            quantities=[25]
        )

        move = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-05-14',
            post=True,
            amounts=[1000],
            company=self.branch_a,
            accounts=[self.purchase_account],
            quantities=[28]
        )

        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")

    def test_tcs_tds_warning_tcs_use_in_bill(self):
        '''
        Test when tcs section is used in the bill creation.
        '''

        move = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-05-29',
            post=True,
            amounts=[100000],
            company=self.branch_a,
            accounts=[self.sale_account],
            quantities=[11]
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
            post=True,
            amounts=[110000],
            company=self.branch_a,
            accounts=[self.purchase_account],
            quantities=[1]
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
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-09-01',
            post=True,
            amounts=[10000],
            company=self.branch_a,
            accounts=[self.business_account],
            quantities=[10]
        )

        self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_b,
            invoice_date='2024-05-01',
            post=True,
            amounts=[10000],
            taxes=[self.tax_194i],
            company=self.branch_a,
            accounts=[self.business_account],
            quantities=[25]
        )

        move = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-07-01',
            post=True,
            amounts=[1000],
            company=self.branch_a,
            accounts=[self.business_account],
            quantities=[10]
        )

        self.assertEqual(move.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194I on this transaction.")

    def test_tcs_tds_warning_all_type_of_invoice_same_account(self):
        '''
        Test when all type of invoices are created with the
        same chart of account.
        '''
        # bill
        move = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-09-01',
            post=True,
            amounts=[10000],
            company=self.branch_a,
            accounts=[self.purchase_account],
            quantities=[10]
        )

        # debit note
        self.reverse_move(move, '2024-09-01')

        # invoice
        move_1 = self.create_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            invoice_date='2024-05-01',
            post=True,
            amounts=[10000],
            company=self.branch_a,
            accounts=[self.purchase_account],
            quantities=[25]
        )

        # credit_note
        self.reverse_move(move_1, '2024-05-01')

        move_2 = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-07-01',
            post=True,
            amounts=[1000],
            company=self.branch_a,
            accounts=[self.purchase_account],
            quantities=[10]
        )
        self.assertEqual(move_2.l10n_in_tcs_tds_warning, False)

    def test_tcs_tds_warning_case_of_entry(self):
        move = self.create_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            invoice_date='2024-06-05',
            post=True,
            amounts=[1000],
            company=self.branch_a,
            accounts=[self.internet_account],
            quantities=[30]
        )
        line = move.invoice_line_ids[0]
        self.assertEqual(move.l10n_in_tcs_tds_warning, False)
        self.assertEqual(line.l10n_in_line_warning, False)

        entry = self.env['account.move'].create({
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'account_id': self.internet_account.id,
                    'partner_id': self.partner_a.id,
                    'debit': 1000.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': self.creditors_account.id,
                    'debit': 0.0,
                    'credit': 1000.0,
                }),
            ]
        })
        entry.action_post()
        self.assertEqual(entry.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194J on this transaction.")

    def test_tcs_tds_warning_case_of_entry_per_transection(self):
        entry = self.env['account.move'].create({
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'account_id': self.building_account.id,
                    'partner_id': self.partner_a.id,
                    'debit': 5100000.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': self.building_account.id,
                    'partner_id': self.partner_a.id,
                    'debit': 2600000.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': self.building_account.id,
                    'partner_id': self.partner_a.id,
                    'debit': 3000000.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': self.creditors_account.id,
                    'debit': 0.0,
                    'credit': 10700000.0,
                }),
            ]
        })
        entry.action_post()
        line = entry.line_ids[0]
        line_1 = entry.line_ids[1]
        line_2 = entry.line_ids[2]
        line_3 = entry.line_ids[3]

        self.assertEqual(line.l10n_in_line_warning, True)
        self.assertEqual(line_1.l10n_in_line_warning, False)
        self.assertEqual(line_2.l10n_in_line_warning, False)
        self.assertEqual(line_3.l10n_in_line_warning, False)
        self.assertEqual(entry.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194IA on this transaction.")

        entry_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'account_id': self.purchase_account.id,
                    'partner_id': self.partner_a.id,
                    'debit': 31000.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': self.purchase_account.id,
                    'partner_id': self.partner_c.id,
                    'tax_ids': [(4, self.tax_194c.id)],
                    'debit': 35000.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': self.creditors_account.id,
                    'debit': 0.0,
                    'credit': 91000.0,
                }),
            ]
        })
        entry_1.action_post()
        line = entry_1.line_ids[0]
        line_1 = entry_1.line_ids[1]
        line_2 = entry_1.line_ids[2]

        self.assertEqual(line.l10n_in_line_warning, True)
        self.assertEqual(line_1.l10n_in_line_warning, False)
        self.assertEqual(line_2.l10n_in_line_warning, False)
        self.assertEqual(entry_1.l10n_in_tcs_tds_warning, "It's advisable to deduct TDS u/s  194C on this transaction.")
