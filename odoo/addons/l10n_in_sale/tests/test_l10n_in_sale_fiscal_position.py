from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

chart_template_ref = 'in'


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestSaleFiscal(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass(chart_template_ref=chart_template_ref)
        # Company
        cls.default_company_state = cls.env.ref('base.state_in_gj')
        cls.default_company = cls.setup_company_data(
            company_name='Odoo In test',
            chart_template=chart_template_ref,
            state_id=cls.default_company_state.id,
        )['company']
        # Partner
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
            'state_id': cls.env.ref('base.state_us_1').id,
            'country_id': cls.env.ref('base.us').id,
        })

    def _assert_order_fiscal_position(self, fpos_ref, partner, post=True):
        test_order = self.env['sale.order'].create({
            'partner_id': partner,
            'company_id': self.env.company.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
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
                partner=self.partner_intra_state.id,
            )

        # Sub-test: Inter-State
        with self.subTest(scenario="Inter-State"):
            self._assert_order_fiscal_position(
                fpos_ref='fiscal_position_in_inter_state',
                partner=self.partner_inter_state.id,
            )

        # Sub-test: Export (Outside India)
        with self.subTest(scenario="Export"):
            sale_order = self._assert_order_fiscal_position(
                fpos_ref='fiscal_position_in_export_sez_in',
                partner=self.partner_foreign.id,
                post=False,
            )

        # Sub-test: SEZ (Special Economic Zone)
        with self.subTest(scenario="SEZ"):
            # Here fpos should Intra-State. But due to `l10n_in_gst_treatment` it will be SEZ
            sale_order = self.env['sale.order'].with_company(self.env.company).create({
                'date_order': fields.Date.from_string('2019-01-01'),
                'partner_id': self.partner_intra_state.id,  # Intra-State Partner
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
