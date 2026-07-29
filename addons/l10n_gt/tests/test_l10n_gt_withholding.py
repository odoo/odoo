# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nGtWithholding(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('gt')
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

    def _register_payment(self, move, **values):
        return self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=move.ids,
        ).create(values)

    # ----------------------------------------
    # ISR withholding
    # ----------------------------------------

    def test_isr_below_threshold(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=2240.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertFalse(self._register_payment(bill).withholding_line_ids)

    def test_isr_below_30000(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_isr_withholding_5_purchase').id,
            'base_amount': 10000.0,
            'amount': 500.0,
        }])

    def test_isr_above_30000(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=56000.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids.sorted('amount'), [
            {'tax_id': self.chart_template.ref('tax_isr_withholding_7_purchase').id, 'base_amount': 20000.0, 'amount': 1400.0},
            {'tax_id': self.chart_template.ref('tax_isr_withholding_5_purchase').id, 'base_amount': 30000.0, 'amount': 1500.0},
        ])

    def test_isr_at_30000(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=33600.0,
            invoice_date='2026-01-01',
            post=True,
        )
        # The 7% bracket applies on the part above Q 30,000 only, none here.
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_isr_withholding_5_purchase').id,
            'base_amount': 30000.0,
            'amount': 1500.0,
        }])

    def test_isr_at_threshold(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        # The threshold must be exceeded, Q 2,499.99 net is not withheld while Q 2,500 is.
        bill_at_threshold = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=2799.99,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertFalse(self._register_payment(bill_at_threshold).withholding_line_ids)

        bill_above_threshold = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=2800.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(bill_above_threshold).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_isr_withholding_5_purchase').id,
            'base_amount': 2500.0,
            'amount': 125.0,
        }])

    def test_isr_withheld_on_payment(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        wizard = self._register_payment(bill)
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 10000.0,
            'amount': 500.0,
        }])

        payment = wizard._create_payments()
        entry_lines = payment.move_id.line_ids
        # Payable 11,200 / outstanding 10,700 / ISR withheld 500 / withholding base 10,000 and its counterpart.
        self.assertEqual(sorted(entry_lines.mapped('balance')), [-10700.0, -10000.0, -500.0, 10000.0, 11200.0])

    def test_isr_on_a_foreign_currency_bill(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        usd = self.setup_other_currency('USD', rates=[('2026-01-01', 0.125)])
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            currency_id=usd,
            invoice_date='2026-01-01',
            post=True,
        )
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
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        wizard = self._register_payment(bill, withhold='withhold')
        self.assertRecordValues(wizard, [{'amount': 500.0}])
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 10000.0,
            'amount': 500.0,
        }])

    def test_isr_withheld_in_full_on_a_partial_payment(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        wizard = self._register_payment(bill, amount=5000.0)
        self.assertRecordValues(wizard.withholding_line_ids, [{'base_amount': 10000.0, 'amount': 500.0}])
        wizard._create_payments()
        self.assertEqual(bill.amount_residual, 6200.0)

        # The withholding is applied once, the next payment only pays the remaining balance.
        wizard = self._register_payment(bill)
        self.assertRecordValues(wizard, [{'withhold': 'payment', 'display_withholding': False, 'amount': 6200.0}])
        self.assertFalse(wizard.withholding_line_ids)

    def test_isr_payment_below_the_withholding_is_blocked(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        wizard = self._register_payment(bill, amount=400.0)
        with self.assertRaises(UserError):
            wizard._create_payments()

    def test_isr_withhold_only_then_pay(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self._register_payment(bill, withhold='withhold')._create_payments()
        self.assertEqual(bill.amount_residual, 10700.0)

        wizard = self._register_payment(bill)
        self.assertRecordValues(wizard, [{'withhold': 'payment', 'display_withholding': False, 'amount': 10700.0}])
        self.assertFalse(wizard.withholding_line_ids)

    def test_isr_payment_only(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        # The withholding due is left aside to be withheld later.
        wizard = self._register_payment(bill, withhold='payment')
        self.assertRecordValues(wizard, [{'amount': 10700.0, 'show_payment_difference': False}])
        wizard._create_payments()
        self.assertEqual(bill.amount_residual, 500.0)

    def test_isr_withholding_after_a_partial_payment_only(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self._register_payment(bill, withhold='payment', amount=5000.0)._create_payments()

        # The base stays the full untaxed amount of the bill.
        wizard = self._register_payment(bill, withhold='withhold')
        self.assertRecordValues(wizard, [{'amount': 500.0}])
        self.assertRecordValues(wizard.withholding_line_ids, [{'base_amount': 10000.0, 'amount': 500.0}])

    def test_isr_base_is_the_bill_untaxed_amount(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        # Two lines of Q 1,500 net: each one alone stays under the Q 2,499.99 threshold, the bill does not.
        bill = self._create_invoice(
            move_type='in_invoice',
            partner_id=self.partner_a,
            invoice_date='2026-01-01',
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_gt, price_unit=1680.0),
                self._prepare_invoice_line(product_id=self.product_gt, price_unit=1680.0),
            ],
            post=True,
        )
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_isr_withholding_5_purchase').id,
            'base_amount': 3000.0,
            'amount': 150.0,
        }])

    def test_isr_scale_is_progressive_on_the_bill_untaxed_amount(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        # Two lines of Q 25,000 net: the bill reaches the 7% bracket while each line alone stays at 5%.
        bill = self._create_invoice(
            move_type='in_invoice',
            partner_id=self.partner_a,
            invoice_date='2026-01-01',
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_gt, price_unit=28000.0),
                self._prepare_invoice_line(product_id=self.product_gt, price_unit=28000.0),
            ],
            post=True,
        )
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids.sorted('amount'), [
            {'tax_id': self.chart_template.ref('tax_isr_withholding_7_purchase').id, 'base_amount': 20000.0, 'amount': 1400.0},
            {'tax_id': self.chart_template.ref('tax_isr_withholding_5_purchase').id, 'base_amount': 30000.0, 'amount': 1500.0},
        ])

    def test_isr_on_vendor_refund(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        refund = self._create_invoice_one_line(
            move_type='in_refund',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(refund).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_isr_withholding_5_purchase').id,
            'base_amount': 10000.0,
            'amount': 500.0,
        }])

    def test_isr_on_customer_refund(self):
        self.partner_a.l10n_gt_isr_withholding_agent = True
        refund = self._create_invoice_one_line(
            move_type='out_refund',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(refund).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_isr_withholding_5_sale').id,
            'base_amount': 10000.0,
            'amount': 500.0,
        }])

    def test_withholding_below_its_scale_is_not_proposed_on_the_payment(self):
        self.company.partner_id.write({
            'l10n_gt_isr_withholding_agent': True,
            'l10n_gt_vat_withholding_type': 'public_sector',  # withholds VAT from Q 30,000 onwards only
        })
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        # Only the ISR withholding is due, the VAT one must not add an empty line nor its base items.
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_isr_withholding_5_purchase').id,
            'base_amount': 10000.0,
            'amount': 500.0,
        }])

    def test_isr_not_applied_when_vendor_is_also_an_agent(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        self.partner_a.l10n_gt_isr_withholding_agent = True
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertFalse(self._register_payment(bill).withholding_line_ids)

    def test_isr_not_applied_when_company_is_not_an_agent(self):
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertFalse(self._register_payment(bill).withholding_line_ids)

    def test_isr_on_customer_invoice(self):
        self.partner_a.l10n_gt_isr_withholding_agent = True
        invoice = self._create_invoice_one_line(
            move_type='out_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(invoice).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_isr_withholding_5_sale').id,
            'base_amount': 10000.0,
            'amount': 500.0,
        }])

    def test_isr_follows_the_customer(self):
        self.partner_b.l10n_gt_isr_withholding_agent = True
        invoice_partner_a = self._create_invoice_one_line(
            move_type='out_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertFalse(self._register_payment(invoice_partner_a).withholding_line_ids)

        # On a customer invoice the customer is the agent, so the withholding follows it.
        invoice_partner_b = self._create_invoice_one_line(
            move_type='out_invoice',
            partner_id=self.partner_b,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(invoice_partner_b).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_isr_withholding_5_sale').id,
            'base_amount': 10000.0,
            'amount': 500.0,
        }])

    def test_isr_archived_tax_is_not_proposed(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        self.chart_template.ref('tax_isr_withholding_5_purchase').active = False
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertFalse(self._register_payment(bill).withholding_line_ids)

    def test_isr_deleted_tax_is_not_proposed(self):
        self.company.partner_id.l10n_gt_isr_withholding_agent = True
        self.chart_template.ref('tax_isr_withholding_5_purchase').unlink()
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertFalse(self._register_payment(bill).withholding_line_ids)

    # ----------------------------------------
    # VAT withholding
    # ----------------------------------------

    def test_vat_special_taxpayer(self):
        self.company.partner_id.l10n_gt_vat_withholding_type = 'special_taxpayer'
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_vat_withholding_15_purchase').id,
            'base_amount': 10000.0,
            'amount': 180.0,
        }])

    def test_vat_public_sector(self):
        self.company.partner_id.l10n_gt_vat_withholding_type = 'public_sector'
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=56000.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_vat_withholding_25_purchase').id,
            'base_amount': 50000.0,
            'amount': 1500.0,
        }])

    def test_vat_public_sector_below_threshold(self):
        self.company.partner_id.l10n_gt_vat_withholding_type = 'public_sector'
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertFalse(self._register_payment(bill).withholding_line_ids)

    def test_vat_exporter_decree_29_89(self):
        self.company.partner_id.l10n_gt_vat_withholding_type = 'exporter_29_89'
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_vat_withholding_65_purchase').id,
            'base_amount': 10000.0,
            'amount': 780.0,
        }])

    def test_vat_exporter_non_agricultural_product(self):
        self.company.partner_id.l10n_gt_vat_withholding_type = 'exporter'
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_vat_withholding_15_purchase').id,
            'base_amount': 10000.0,
            'amount': 180.0,
        }])

    def test_vat_exporter_agricultural_product(self):
        self.company.partner_id.l10n_gt_vat_withholding_type = 'exporter'
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_agricultural,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_vat_withholding_65_purchase').id,
            'base_amount': 10000.0,
            'amount': 780.0,
        }])

    def test_vat_exporter_bases_are_split_per_rate(self):
        self.company.partner_id.l10n_gt_vat_withholding_type = 'exporter'
        bill = self._create_invoice(
            move_type='in_invoice',
            partner_id=self.partner_a,
            invoice_date='2026-01-01',
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_agricultural, price_unit=1400.0),
                self._prepare_invoice_line(product_id=self.product_agricultural, price_unit=1400.0),
                self._prepare_invoice_line(product_id=self.product_gt, price_unit=5600.0),
            ],
            post=True,
        )
        # Q 2,500 of agricultural goods withheld at 7.8% and Q 5,000 of other goods at 1.8%.
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids.sorted('base_amount'), [
            {'tax_id': self.chart_template.ref('tax_vat_withholding_65_purchase').id, 'base_amount': 2500.0, 'amount': 195.0},
            {'tax_id': self.chart_template.ref('tax_vat_withholding_15_purchase').id, 'base_amount': 5000.0, 'amount': 90.0},
        ])

    def test_vat_exporter_threshold_is_on_the_bill_untaxed_amount(self):
        self.company.partner_id.l10n_gt_vat_withholding_type = 'exporter'
        bill = self._create_invoice(
            move_type='in_invoice',
            partner_id=self.partner_a,
            invoice_date='2026-01-01',
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_agricultural, price_unit=2240.0),
                self._prepare_invoice_line(product_id=self.product_gt, price_unit=5600.0),
            ],
            post=True,
        )
        # The Q 2,000 of agricultural goods stay under the Q 2,499.99 threshold alone, the bill does not.
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids.sorted('base_amount'), [
            {'tax_id': self.chart_template.ref('tax_vat_withholding_65_purchase').id, 'base_amount': 2000.0, 'amount': 156.0},
            {'tax_id': self.chart_template.ref('tax_vat_withholding_15_purchase').id, 'base_amount': 5000.0, 'amount': 90.0},
        ])

    def test_vat_not_applied_when_vendor_is_also_an_agent(self):
        self.company.partner_id.l10n_gt_vat_withholding_type = 'special_taxpayer'
        self.partner_a.l10n_gt_vat_withholding_type = 'special_taxpayer'
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertFalse(self._register_payment(bill).withholding_line_ids)

    def test_vat_not_applied_when_company_is_not_an_agent(self):
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertFalse(self._register_payment(bill).withholding_line_ids)

    def test_vat_follows_the_customer_regime(self):
        self.partner_a.l10n_gt_vat_withholding_type = 'special_taxpayer'
        invoice = self._create_invoice_one_line(
            move_type='out_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(invoice).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_vat_withholding_15_sale').id,
            'base_amount': 10000.0,
            'amount': 180.0,
        }])

    def test_vat_on_vendor_refund(self):
        self.company.partner_id.l10n_gt_vat_withholding_type = 'special_taxpayer'
        refund = self._create_invoice_one_line(
            move_type='in_refund',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(refund).withholding_line_ids, [{
            'tax_id': self.chart_template.ref('tax_vat_withholding_15_purchase').id,
            'base_amount': 10000.0,
            'amount': 180.0,
        }])

    def test_vat_archived_tax_is_not_proposed(self):
        self.company.partner_id.l10n_gt_vat_withholding_type = 'special_taxpayer'
        self.chart_template.ref('tax_vat_withholding_15_purchase').active = False
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertFalse(self._register_payment(bill).withholding_line_ids)

    def test_isr_and_vat_withheld_together(self):
        self.company.partner_id.write({
            'l10n_gt_isr_withholding_agent': True,
            'l10n_gt_vat_withholding_type': 'special_taxpayer',
        })
        bill = self._create_invoice_one_line(
            move_type='in_invoice',
            partner_id=self.partner_a,
            product_id=self.product_gt,
            price_unit=11200.0,
            invoice_date='2026-01-01',
            post=True,
        )
        self.assertRecordValues(self._register_payment(bill).withholding_line_ids.sorted('amount'), [
            {'tax_id': self.chart_template.ref('tax_vat_withholding_15_purchase').id, 'base_amount': 10000.0, 'amount': 180.0},
            {'tax_id': self.chart_template.ref('tax_isr_withholding_5_purchase').id, 'base_amount': 10000.0, 'amount': 500.0},
        ])
