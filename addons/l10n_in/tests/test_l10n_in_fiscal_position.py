from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

chart_template_ref = 'in'


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestFiscal(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.default_company_state = cls.env.ref('base.state_in_gj')
        cls.default_company = cls.setup_company_data(
            company_name='Odoo In test',
            chart_template=chart_template_ref,
            state_id=cls.default_company_state.id,
        )['company']
        cls.outside_in_company = cls.setup_company_data(
            company_name='Outside India Company',
            chart_template=False,
            country_id=cls.env.ref('base.us').id,
        )['company']
        cls.env.company = cls.default_company
        cls.partner_intra_state = cls.partner_a.copy({
            'state_id': cls.default_company_state.id,
            'country_id': cls.env.ref('base.in').id,
        })
        cls.partner_inter_state = cls.partner_b.copy({
            'state_id': cls.env.ref('base.state_in_mh').id,
            'country_id': cls.env.ref('base.in').id,
        })
        cls.partner_foreign = cls.env['res.partner'].create({
            'name': 'Partner Outside India',
            'country_id': cls.env.ref('base.us').id,
        })

    def _assert_in_intra_state_fiscal_with_company(self, companies):
        for company in companies:
            state = company.state_id
            name = state and 'Within %s' % state.name or 'Intra State'
            self.assertRecordValues(
                self.env['account.chart.template'].with_company(company).ref('fiscal_position_in_intra_state'),
                [{
                    'name': name,
                    'state_ids': state.ids,
                    'company_id': company.id,  # To make sure for branches don't get parent fiscal position
                    'auto_apply': True
                }]
            )

    def _assert_invoice_fiscal_position(self, fiscal_position_ref, partner, tax_ref='igst_sale_18'):
        test_invoice = self.init_invoice(
            move_type="out_invoice",
            partner=partner,
            post=True,
            amounts=[110, 500],
            taxes=self.env['account.chart.template'].ref(tax_ref)
        )
        self.assertEqual(test_invoice.fiscal_position_id, self.env['account.chart.template'].ref(fiscal_position_ref))

    def test_l10n_in_setting_up_company(self):
        company = self.setup_company_data(company_name='Fiscal Setup Test Company', chart_template=chart_template_ref)['company']
        # Test with no state but country india
        self._assert_in_intra_state_fiscal_with_company(company)
        # Change state
        company.write({'state_id': self.default_company_state.id})
        self._assert_in_intra_state_fiscal_with_company(company)
        # Change State Again
        company.write({'state_id': self.env.ref('base.state_in_ap')})
        self._assert_in_intra_state_fiscal_with_company(company)

    def test_l10n_in_auto_apply_fiscal_invoices(self):
        self._assert_in_intra_state_fiscal_with_company(self.env.company)
        # Intra State
        self._assert_invoice_fiscal_position(
            fiscal_position_ref='fiscal_position_in_intra_state',
            partner=self.partner_intra_state,
            tax_ref='sgst_sale_18'
        )
        # Inter State
        self._assert_invoice_fiscal_position(
            fiscal_position_ref='fiscal_position_in_inter_state',
            partner=self.partner_inter_state
        )
        # Outside India
        self._assert_invoice_fiscal_position(
            fiscal_position_ref='fiscal_position_in_export_sez_in',
            partner=self.partner_foreign
        )

    def test_l10n_in_fiscal_for_branch(self):
        branch_1 = self.setup_company_data(
            company_name='Branch 1',
            chart_template=chart_template_ref,
            parent_id=self.default_company.id,
            state_id=self.partner_inter_state.state_id.id,  # Setting Partner B state will be now Intra State for branch 1
            account_fiscal_country_id=self.env.ref('base.in').id,
        )['company']
        self.env.company = self.outside_in_company
        branch_2 = self.env['res.company'].create({
            'name': 'Branch 2',
            'parent_id': self.default_company.id,
            'account_fiscal_country_id': self.env.ref('base.in').id,
            'country_id': self.env.ref('base.in').id,
        })
        # Check Branch with country india and no state
        self._assert_in_intra_state_fiscal_with_company(branch_2)
        # Set state after creating branch
        branch_2.write({'state_id': self.env.ref('base.state_in_mp').id})
        self._assert_in_intra_state_fiscal_with_company(branch_1 + branch_2)
        # Invoice fiscal test with branch
        self.env.company = branch_1
        self._assert_invoice_fiscal_position(
            fiscal_position_ref='fiscal_position_in_intra_state',
            partner=self.partner_inter_state,
            tax_ref='sgst_sale_18'
        )
        self._assert_invoice_fiscal_position(
            fiscal_position_ref='fiscal_position_in_inter_state',
            partner=self.partner_intra_state
        )
        self._assert_invoice_fiscal_position(
            fiscal_position_ref='fiscal_position_in_export_sez_in',
            partner=self.partner_foreign
        )
