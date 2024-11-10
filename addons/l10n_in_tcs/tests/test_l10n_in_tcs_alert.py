from odoo import Command
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nInTcsAlert(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ChartTemplate = cls.env['account.chart.template']

        cls.company.write({'l10n_in_tcs': True})

        # ==== Chart of Accounts ====
        cls.sale_account = ChartTemplate.ref('p20011')
        cls.sale_account.write({
            'l10n_in_tds_tcs_section_id': cls.env.ref('l10n_in_tcs.tcs_section_206c1g_r').id
        })

        # ==== Taxes ====
        cls.tax_206c1g_r = ChartTemplate.ref('tcs_5_us_206c_1g_som')
        cls.tax_206c1g_r.write({'l10n_in_section_id': cls.env.ref('l10n_in_tcs.tcs_section_206c1g_r').id})

        country_in_id = cls.env.ref("base.in").id

        # ==== Partners ====
        cls.partner_a.write({
            'l10n_in_pan': 'ABCPM8965E'
        })

        # ==== Company ====
        cls.env.company.write({
            'child_ids': [
                Command.create({
                    'name': 'Branch A',
                    "state_id": cls.env.ref("base.state_in_gj").id,
                    'account_fiscal_country_id': country_in_id,
                    'country_id': country_in_id,
                }),
            ],
        })
        cls.cr.precommit.run()  # load the CoA
        cls.branch_a = cls.env.company.child_ids

    def create_invoice(self, move_type=None, partner=None, invoice_date=None, amounts=None, taxes=[], company=None, accounts=[], quantities=[]):
        invoice = self.init_invoice(
            move_type=move_type or 'out_invoice',
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

    def test_tcs_warning_cleared_on_available_tax(self):
        '''
        Test when a tax is added to the move line with a similar tax group
        as the account.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[710000],
            taxes=[self.tax_206c1g_r],
            company=self.branch_a,
        )
        self.assertEqual(move.l10n_in_warning, False)

    def test_tcs_warning_use_in_bill(self):
        '''
        Test when tcs section is used in the bill creation.
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2024-05-29',
            move_type='in_invoice',
            amounts=[1100000],
            company=self.branch_a,
            accounts=[self.sale_account]
        )
        self.assertEqual(move.l10n_in_warning, False)

    def test_tcs_warning_if_some_lines_has_tax(self):
        '''
        Test when a tax is added to the some of the move line
        '''

        move = self.create_invoice(
            partner=self.partner_a,
            invoice_date='2022-12-12',
            amounts=[710000, 710000],
            taxes=[self.tax_206c1g_r],
            company=self.branch_a,
        )
        self.assertEqual(move.l10n_in_warning['tcs_threshold_alert']['message'], "It's advisable to collect TCS u/s 206C(1G) Remittance on this transaction.")
