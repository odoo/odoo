from odoo.tests import tagged

from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestFiscal(L10nInTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Remove fiscal position 'fiscal_pos_a' so it does not show up on invoice
        cls.partner_b.property_account_position_id = None

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

    def _assert_invoice_fiscal_position(self, fiscal_position_ref, partner, taxes):
        test_invoice = self.init_invoice(
            move_type="out_invoice",
            partner=partner,
            post=True,
            amounts=[110, 500],
            taxes=taxes
        )
        self.assertEqual(test_invoice.fiscal_position_id, self.env['account.chart.template'].ref(fiscal_position_ref))

    def test_l10n_in_setting_up_company(self):
        company = self._create_company(name='Fiscal Setup Test Company')
        # Test with no state but country india
        self._assert_in_intra_state_fiscal_with_company(company)
        # Change state
        company.write({'state_id': self.default_company.state_id.id})
        self._assert_in_intra_state_fiscal_with_company(company)
        # Change State Again
        company.write({'state_id': self.env.ref('base.state_in_ap')})
        self._assert_in_intra_state_fiscal_with_company(company)

    def test_l10n_in_auto_apply_fiscal_invoices(self):
        self._assert_in_intra_state_fiscal_with_company(self.default_company)

        # Intra State
        self._assert_invoice_fiscal_position(
            fiscal_position_ref='fiscal_position_in_intra_state',
            partner=self.partner_a,
            taxes=self.sgst_sale_18,
        )
        # Inter State
        self._assert_invoice_fiscal_position(
            fiscal_position_ref='fiscal_position_in_inter_state',
            partner=self.partner_b,
            taxes=self.igst_sale_18,
        )
        # Outside India
        self._assert_invoice_fiscal_position(
            fiscal_position_ref='fiscal_position_in_export_sez_in',
            partner=self.partner_foreign,
            taxes=self.igst_sale_18,
        )

    def test_l10n_in_fiscal_for_branch(self):
        branch_1 = self._create_company(
            name='Branch 1',
            parent_id=self.default_company.id,
            state_id=self.partner_b.state_id.id,  # Setting Partner B state will be now Intra State for branch 1
            account_fiscal_country_id=self.country_in.id,
        )
        self.env.company = self.outside_in_company
        branch_2 = self.env['res.company'].create({
            'name': 'Branch 2',
            'parent_id': self.default_company.id,
            'account_fiscal_country_id': self.country_in.id,
            'country_id': self.country_in.id,
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
            partner=self.partner_b,
            taxes=self.sgst_sale_18,
        )
        self._assert_invoice_fiscal_position(
            fiscal_position_ref='fiscal_position_in_inter_state',
            partner=self.partner_a,
            taxes=self.igst_sale_18,
        )
        self._assert_invoice_fiscal_position(
            fiscal_position_ref='fiscal_position_in_export_sez_in',
            partner=self.partner_foreign,
            taxes=self.igst_sale_18,
        )
