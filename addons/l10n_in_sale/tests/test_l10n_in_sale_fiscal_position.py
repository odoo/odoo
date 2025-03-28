from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestSaleFiscal(L10nInTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Remove fiscal position 'property_account_position_id' so it does not show up on orders
        cls.partner_b.property_account_position_id = None

    def _assert_order_fiscal_position(self, fpos_ref, partner, post=True):
        test_order = self.env['sale.order'].create({
            'partner_id': partner,
            'company_id': self.env.company.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 10,
                }),
            ],
        })
        if post:
            test_order.action_confirm()
        self.assertEqual(
            test_order.fiscal_position_id,
            self.env['account.chart.template'].with_company(self.env.company).ref(fpos_ref)
        )
        return test_order

    def test_l10n_in_sale_fiscal_position(self):
        '''
        According to GST: Compare place of supply (instead of delivery address) with company state
        '''

        self.env.company = self.default_company
        template = self.env['account.chart.template']
        company_state = self.env.company.state_id

        # Sub-test: Intra-State
        with self.subTest(scenario="Intra-State"):
            self._assert_order_fiscal_position(
                fpos_ref='fiscal_position_in_intra_state',
                partner=self.partner_a.id,
            )

        # Sub-test: Inter-State
        with self.subTest(scenario="Inter-State"):
            self._assert_order_fiscal_position(
                fpos_ref='fiscal_position_in_inter_state',
                partner=self.partner_b.id,
            )

        # Sub-test: Export (Outside India)
        with self.subTest(scenario="Export"):
            self._assert_order_fiscal_position(
                fpos_ref='fiscal_position_in_export_sez_in',
                partner=self.partner_foreign.id,
            )

        # Sub-test: SEZ (Special Economic Zone)
        with self.subTest(scenario="SEZ"):
            # Here fpos should Intra-State. But due to `l10n_in_gst_treatment` it will be SEZ
            sale_order = self.env['sale.order'].with_company(self.env.company).create({
                'date_order': fields.Date.from_string('2019-01-01'),
                'partner_id': self.partner_a.id,  # Intra-State Partner
                'l10n_in_gst_treatment': 'special_economic_zone',
                'order_line': [Command.create({
                    'product_id': self.product_a.id,
                    'product_uom_qty': 10,
                    'name': 'product test 1',
                    'price_unit': 40,
                })]
            })

            self.assertEqual(
                sale_order.fiscal_position_id,
                template.ref('fiscal_position_in_export_sez_in')
            )

        # Sub-test: Manual Partner Fiscal Check
        with self.subTest(scenario="Manual Partner Fiscal Check"):
            # Here fpos should Inter-State. But due to `property_account_position_id` it will be Export/SEZ
            self.partner_a.write({
                'state_id': company_state.id,  # Company State
                'property_account_position_id': template.ref('fiscal_position_in_export_sez_in').id
            })
            self._assert_order_fiscal_position(
                fpos_ref='fiscal_position_in_export_sez_in',
                partner=self.partner_a.id,
            )
