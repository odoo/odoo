# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nGtWithholding(AccountTestInvoicingCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country('gt')
    @AccountTestInvoicingCommon.setup_chart_template('gt')
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.chart_template = cls.env['account.chart.template'].with_company(cls.company)

        cls.product_gt = cls._create_product(
            name="GT product",
            taxes_id=[Command.set(cls.tax_sale_a.ids)],
            supplier_taxes_id=[Command.set(cls.tax_purchase_a.ids)],
        )
        cls.product_agricultural = cls._create_product(
            name="Cardamom",
            l10n_gt_agricultural_product=True,
            taxes_id=[Command.set(cls.tax_sale_a.ids)],
            supplier_taxes_id=[Command.set(cls.tax_purchase_a.ids)],
        )

    def _create_bill(self, *price_units, product=None):
        return self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': (product or self.product_gt).id,
                    'price_unit': price_unit,
                })
                for price_unit in price_units
            ],
        })

    def _create_invoice(self, partner):
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_gt.id,
                'price_unit': 11200.0,
            })],
        })

    def _register_payment(self, bill, **values):
        if bill.state == 'draft':
            bill.action_post()
        return self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=bill.ids,
        ).create(values)

    def _assert_withholding(self, bill, tax_template_id, expected_amount):
        withholding_lines = self._register_payment(bill).withholding_line_ids
        if tax_template_id:
            self.assertIn(self.chart_template.ref(tax_template_id), withholding_lines.tax_id)
        else:
            self.assertFalse(withholding_lines)
        self.assertEqual(sum(withholding_lines.mapped('amount')), expected_amount)

    # ----------------------------------------
    # ISR withholding
    # ----------------------------------------

    def test_isr_below_threshold(self):
        self.company.l10n_gt_isr_withholding_agent = True
        self._assert_withholding(self._create_bill(2240.0), None, 0.0)

    def test_isr_below_30000(self):
        self.company.l10n_gt_isr_withholding_agent = True
        self._assert_withholding(self._create_bill(11200.0), 'tax_isr_withholding_5_purchase', 500.0)

    def test_isr_above_30000(self):
        self.company.l10n_gt_isr_withholding_agent = True
        self._assert_withholding(self._create_bill(56000.0), 'tax_isr_withholding_7_purchase', 2900.0)

    def test_isr_at_30000(self):
        self.company.l10n_gt_isr_withholding_agent = True
        # The 7% bracket applies on the part above Q 30,000 only, none here.
        self.assertRecordValues(self._register_payment(self._create_bill(33600.0)).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_isr_withholding_5_purchase').id,
            'base_amount': 30000.0,
            'amount': 1500.0,
        }])

    def test_isr_withheld_on_payment(self):
        self.company.l10n_gt_isr_withholding_agent = True
        wizard = self._register_payment(self._create_bill(11200.0))
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 10000.0,
            'amount': 500.0,
        }])

        payment = wizard._create_payments()
        entry_lines = payment.move_id.line_ids
        # Payable 11,200 / outstanding 10,700 / ISR withheld 500 / withholding base 10,000 and its counterpart.
        self.assertEqual(sorted(entry_lines.mapped('balance')), [-10700.0, -10000.0, -500.0, 10000.0, 11200.0])

    def test_isr_on_a_foreign_currency_bill(self):
        self.company.l10n_gt_isr_withholding_agent = True
        usd = self.setup_other_currency('USD', rates=[('2026-01-01', 0.125)])
        bill = self._create_bill(11200.0)
        bill.currency_id = usd
        # Q 80,000 net at 8 GTQ/USD: the scale applies on the company currency amount, Q 1,500 + Q 3,500 withheld.
        wizard = self._register_payment(bill)
        self.assertRecordValues(wizard.withholding_line_ids.sorted('amount'), [
            {'base_amount': 3750.0, 'amount': 187.5},
            {'base_amount': 6250.0, 'amount': 437.5},
        ])

        entry_lines = wizard._create_payments().move_id.line_ids
        self.assertEqual(sum(entry_lines.filtered('tax_line_id').mapped('balance')), -5000.0)
        self.assertEqual(sum(entry_lines.filtered('tax_line_id').mapped('amount_currency')), -625.0)

    def test_isr_withhold_only(self):
        self.company.l10n_gt_isr_withholding_agent = True
        wizard = self._register_payment(self._create_bill(11200.0), withhold='withhold')
        self.assertRecordValues(wizard, [{'amount': 500.0}])
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 10000.0,
            'amount': 500.0,
        }])

    def test_isr_base_is_the_bill_untaxed_amount(self):
        self.company.l10n_gt_isr_withholding_agent = True
        # Two lines of Q 1,250 net: each one alone stays under the Q 2,500 threshold, the bill does not.
        self._assert_withholding(self._create_bill(1400.0, 1400.0), 'tax_isr_withholding_5_purchase', 125.0)

    def test_isr_scale_is_progressive_on_the_bill_untaxed_amount(self):
        self.company.l10n_gt_isr_withholding_agent = True
        # Two lines of Q 25,000 net: the bill reaches the 7% bracket while each line alone stays at 5%.
        bill = self._create_bill(28000.0, 28000.0)
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids.sorted('amount'), [
            {'tax_id': self.chart_template.ref('tax_isr_withholding_7_purchase').id, 'base_amount': 20000.0, 'amount': 1400.0},
            {'tax_id': self.chart_template.ref('tax_isr_withholding_5_purchase').id, 'base_amount': 30000.0, 'amount': 1500.0},
        ])

    def test_withholding_below_its_scale_is_not_proposed_on_the_payment(self):
        self.company.write({
            'l10n_gt_isr_withholding_agent': True,
            'l10n_gt_vat_withholding_type': 'public_sector',  # withholds VAT from Q 30,000 onwards only
        })
        # Only the ISR withholding is due, the VAT one must not add an empty line nor its base items.
        self.assertRecordValues(self._register_payment(self._create_bill(11200.0)).withholding_line_ids, [{
            'base_amount': 10000.0,
            'amount': 500.0,
        }])

    def test_isr_not_applied_when_vendor_is_also_an_agent(self):
        self.company.l10n_gt_isr_withholding_agent = True
        self.partner_a.l10n_gt_isr_withholding_agent = True
        self._assert_withholding(self._create_bill(11200.0), None, 0.0)

    def test_isr_not_applied_when_company_is_not_an_agent(self):
        self._assert_withholding(self._create_bill(11200.0), None, 0.0)

    def test_isr_on_customer_invoice(self):
        self.partner_a.l10n_gt_isr_withholding_agent = True
        self._assert_withholding(self._create_invoice(self.partner_a), 'tax_isr_withholding_5_sale', 500.0)

    def test_isr_follows_the_customer(self):
        self.partner_b.l10n_gt_isr_withholding_agent = True
        self._assert_withholding(self._create_invoice(self.partner_a), None, 0.0)

        # On a customer invoice the customer is the agent, so the withholding follows it.
        self._assert_withholding(self._create_invoice(self.partner_b), 'tax_isr_withholding_5_sale', 500.0)

    # ----------------------------------------
    # VAT withholding
    # ----------------------------------------

    def test_vat_special_taxpayer(self):
        self.company.l10n_gt_vat_withholding_type = 'special_taxpayer'
        self._assert_withholding(self._create_bill(11200.0), 'tax_vat_withholding_15_purchase', 180.0)

    def test_vat_public_sector(self):
        self.company.l10n_gt_vat_withholding_type = 'public_sector'
        self._assert_withholding(self._create_bill(56000.0), 'tax_vat_withholding_25_purchase', 1500.0)

    def test_vat_public_sector_below_threshold(self):
        self.company.l10n_gt_vat_withholding_type = 'public_sector'
        self._assert_withholding(self._create_bill(11200.0), None, 0.0)

    def test_vat_exporter_decree_29_89(self):
        self.company.l10n_gt_vat_withholding_type = 'exporter_29_89'
        self._assert_withholding(self._create_bill(11200.0), 'tax_vat_withholding_65_purchase', 780.0)

    def test_vat_exporter_non_agricultural_product(self):
        self.company.l10n_gt_vat_withholding_type = 'exporter'
        self._assert_withholding(self._create_bill(11200.0), 'tax_vat_withholding_15_purchase', 180.0)

    def test_vat_exporter_agricultural_product(self):
        self.company.l10n_gt_vat_withholding_type = 'exporter'
        bill = self._create_bill(11200.0, product=self.product_agricultural)
        self._assert_withholding(bill, 'tax_vat_withholding_65_purchase', 780.0)

    def test_vat_exporter_bases_are_split_per_rate(self):
        self.company.l10n_gt_vat_withholding_type = 'exporter'
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                Command.create({'product_id': self.product_agricultural.id, 'price_unit': 1400.0}),
                Command.create({'product_id': self.product_agricultural.id, 'price_unit': 1400.0}),
                Command.create({'product_id': self.product_gt.id, 'price_unit': 5600.0}),
            ],
        })
        # Q 2,500 of agricultural goods withheld at 7.8% and Q 5,000 of other goods at 1.8%.
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids.sorted('base_amount'), [
            {'base_amount': 2500.0, 'amount': 195.0},
            {'base_amount': 5000.0, 'amount': 90.0},
        ])

    def test_vat_exporter_threshold_is_on_the_bill_untaxed_amount(self):
        self.company.l10n_gt_vat_withholding_type = 'exporter'
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [
                Command.create({'product_id': self.product_agricultural.id, 'price_unit': 2240.0}),
                Command.create({'product_id': self.product_gt.id, 'price_unit': 5600.0}),
            ],
        })
        # The Q 2,000 of agricultural goods stay under the Q 2,500 threshold alone, the bill does not.
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids.sorted('base_amount'), [
            {'base_amount': 2000.0, 'amount': 156.0},
            {'base_amount': 5000.0, 'amount': 90.0},
        ])

    def test_vat_not_applied_when_vendor_is_also_an_agent(self):
        self.company.l10n_gt_vat_withholding_type = 'special_taxpayer'
        self.partner_a.l10n_gt_vat_withholding_type = 'special_taxpayer'
        self._assert_withholding(self._create_bill(11200.0), None, 0.0)

    def test_vat_not_applied_when_company_is_not_an_agent(self):
        self._assert_withholding(self._create_bill(11200.0), None, 0.0)

    def test_vat_follows_the_customer_regime(self):
        self.partner_a.l10n_gt_vat_withholding_type = 'special_taxpayer'
        self._assert_withholding(self._create_invoice(self.partner_a), 'tax_vat_withholding_15_sale', 180.0)

    def test_isr_and_vat_withheld_together(self):
        self.company.write({
            'l10n_gt_isr_withholding_agent': True,
            'l10n_gt_vat_withholding_type': 'special_taxpayer',
        })
        self.assertRecordValues(self._register_payment(self._create_bill(11200.0)).withholding_line_ids.sorted('amount'), [
            {'tax_id': self.chart_template.ref('tax_vat_withholding_15_purchase').id, 'amount': 180.0},
            {'tax_id': self.chart_template.ref('tax_isr_withholding_5_purchase').id, 'amount': 500.0},
        ])
