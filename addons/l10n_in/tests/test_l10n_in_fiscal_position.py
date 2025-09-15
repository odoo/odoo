from odoo import Command, fields
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

    def _assert_invoice_fiscal_position(self, fiscal_position_ref, partner, taxes, move_type='out_invoice', post=True):
        test_invoice = self.init_invoice(
            move_type=move_type,
            partner=partner,
            post=post,
            amounts=[110, 500],
            taxes=taxes
        )
        self.assertEqual(test_invoice.fiscal_position_id, self.env['account.chart.template'].ref(fiscal_position_ref))
        return test_invoice

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

    def test_l10n_in_fiscal_in_bill_to_ship_to(self):
        self.env.company = self.default_company
        # Inter State
        out_invoice = self._assert_invoice_fiscal_position(
            fiscal_position_ref='fiscal_position_in_inter_state',
            partner=self.partner_b,
            taxes=self.igst_sale_18,
            post=False,
        )
        # Intra State
        out_invoice.write({
            'l10n_in_state_id': self.env.ref('base.state_in_gj').id,
        })
        self.assertEqual(
            out_invoice.fiscal_position_id,
            self.env['account.chart.template'].ref('fiscal_position_in_intra_state')
        )
        # Outside India (Export/SEZ)
        out_invoice.write({
            'l10n_in_state_id': self.env.ref('l10n_in.state_in_oc').id,  # Other Country State
        })
        self.assertEqual(
            out_invoice.fiscal_position_id,
            self.env['account.chart.template'].ref('fiscal_position_in_export_sez_in')
        )

    def test_l10n_in_fiscal_in_vendor_bills(self):
        '''
        In Purchase Document: Compare place of supply with vendor state
        '''

        self.env.company = self.default_company
        template = self.env['account.chart.template']
        company_state = self.env.company.state_id
        other_state = self.env['res.country.state'].search([
            ('id', '!=', company_state.id),
            ('country_id', '=', company_state.country_id.id)
        ], limit=1)

        # Sub-test: Intra-State
        with self.subTest(scenario="Intra-State"):
            self.partner_a.write({'state_id': company_state.id})
            self.partner_a.write({'country_id': company_state.country_id.id})
            vendor_bill = self._assert_invoice_fiscal_position(
                fiscal_position_ref='fiscal_position_in_intra_state',
                partner=self.partner_a,
                move_type='in_invoice',
                taxes=self.igst_sale_18,
                post=False,
            )
            self.partner_a.write({'state_id': other_state.id})
            vendor_bill.write({'l10n_in_state_id': other_state.id})
            self.assertEqual(
                vendor_bill.fiscal_position_id,
                template.ref('fiscal_position_in_intra_state')
            )

        # Sub-test: Inter-State
        with self.subTest(scenario="Inter-State"):
            self.partner_a.write({'state_id': other_state.id})
            vendor_bill = self._assert_invoice_fiscal_position(
                fiscal_position_ref='fiscal_position_in_inter_state',
                partner=self.partner_a,
                move_type='in_invoice',
                taxes=self.igst_sale_18,
                post=False,
            )
            self.partner_a.write({'state_id': company_state.id})
            vendor_bill.write({'l10n_in_state_id': other_state.id})
            self.assertEqual(
                vendor_bill.fiscal_position_id,
                template.ref('fiscal_position_in_inter_state')
            )

        # Sub-test: Export/SEZ (Outside India)
        with self.subTest(scenario="Export/SEZ"):
            vendor_bill = self._assert_invoice_fiscal_position(
                fiscal_position_ref='fiscal_position_in_export_sez_in',
                partner=self.partner_foreign,
                move_type='in_invoice',
                taxes=self.igst_sale_18,
                post=False,
            )
            vendor_bill.write({'l10n_in_state_id': self.env.ref('l10n_in.state_in_oc').id})  # Other Country State
            self.assertEqual(
                vendor_bill.fiscal_position_id,
                template.ref('fiscal_position_in_export_sez_in')
            )
            # Here fpos should Inter-State. But due to `l10n_in_gst_treatment` it will be Export/SEZ
            self.partner_a.write({'state_id': other_state.id})
            vendor_bill.write({
                'partner_id': self.partner_a.id,  # Inter-State Partner
                'l10n_in_state_id': company_state.id,  # Company State
                'l10n_in_gst_treatment': 'special_economic_zone',
            })
            self.assertEqual(
                vendor_bill.fiscal_position_id,
                template.ref('fiscal_position_in_export_sez_in')
            )

        # Sub-test: Manual Partner Fiscal Check
        with self.subTest(scenario="Manual Partner Fiscal Check"):
            # Here fpos should Inter-State. But due to `property_account_position_id` it will be Export/SEZ
            self.partner_a.write({
                'state_id': company_state.id,  # Intra-State Partner
                'property_account_position_id': template.ref('fiscal_position_in_export_sez_in').id
            })
            vendor_bill = self.env['account.move'].with_company(self.env.company).create({
                'move_type': 'in_invoice',
                'invoice_date': fields.Date.from_string('2019-01-01'),
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 10,
                    'name': 'product test 1',
                    'price_unit': 40,
                })]
            })
            vendor_bill.action_post()
    
            self.assertEqual(
                vendor_bill.fiscal_position_id,
                self.env['account.chart.template'].ref('fiscal_position_in_export_sez_in')
            )

    def test_l10n_in_company_with_no_vat(self):
        """
        Test the company with no VAT and update the partner and company states as per the GSTIN number
        """
        company = self.default_company

        company.write({'vat': False})
        self.assertFalse(company.vat)
        company.action_update_state_as_per_gstin()
        self.assertEqual(company.partner_id.state_id, self.env.ref('base.state_in_gj'))

        company.write({'vat': '36AABCT1332L011'})
        company.action_update_state_as_per_gstin()
        self.assertEqual(company.state_id, self.env.ref('base.state_in_ts'))
