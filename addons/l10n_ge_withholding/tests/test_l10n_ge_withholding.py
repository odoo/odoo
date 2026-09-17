from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nGeWithholding(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ge")
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data["company"].withholding_tax_base_account_id = cls.env["account.account"].create({
            "code": "WITHB",
            "name": "Withholding Tax Base Account",
            "account_type": "asset_current",
        })
        cls.outstanding_account = cls.env["account.account"].create({
            "code": "OSTP420",
            "name": "Outstanding Payments",
            "account_type": "asset_current",
        })
        withholding_sequence = cls.env["ir.sequence"].create({
            "implementation": "no_gap",
            "name": "Withholding Sequence",
            "padding": 4,
            "number_increment": 1,
        })
        chart_template = cls.env["account.chart.template"].with_company(cls.company_data["company"])
        cls.tax_services = chart_template.ref("ge_tax_wh_10_s")
        cls.tax_dividends = chart_template.ref("ge_tax_wh_5_d")
        (cls.tax_services + cls.tax_dividends).withholding_sequence_id = withholding_sequence
        cls.currency_eur = cls.setup_other_currency("EUR", rates=[("1900-01-01", 1 / 3)])

    def _get_tag(self, name):
        return self.env["account.account.tag"].search([("name", "=", name), ("country_id.code", "=", "GE")])

    def _register_payment_with_withholding(self, bill, withholding_lines_vals=None):
        payment_register = self.env["account.payment.register"]\
            .with_context(active_model="account.move", active_ids=bill.ids)\
            .create({})
        payment_register.withholding_outstanding_account_id = self.outstanding_account
        if withholding_lines_vals is not None:
            payment_register.withhold = "withhold_pay"
            payment_register.withholding_line_ids = [Command.clear()] + [
                Command.create(line_vals) for line_vals in withholding_lines_vals
            ]
        return payment_register._create_payments()

    def test_treaty_exempt_amount_on_withholding_tax_line(self):
        """ The treaty exempt amount of the withholding lines is carried onto the withholding tax journal item
        in company currency, converted and signed like its base amount, and summed over merged lines.
        """
        bill = self._create_invoice_one_line(
            move_type="in_invoice", currency_id=self.currency_eur, price_unit=11000.0, post=True,
        )
        payment = self._register_payment_with_withholding(bill, [
            {"tax_id": self.tax_services.id, "base_amount": 6000.0, "l10n_ge_treaty_exempt_amount": 100.0},
            {"tax_id": self.tax_services.id, "base_amount": 4000.0, "l10n_ge_treaty_exempt_amount": 50.0},
            {"tax_id": self.tax_dividends.id, "base_amount": 1000.0},
        ])
        withholding_tax_lines = payment.move_id.line_ids.filtered("tax_line_id").sorted("balance")
        self.assertRecordValues(withholding_tax_lines, [
            {
                "tax_line_id": self.tax_services.id,
                "amount_currency": -1000.0,
                "balance": -3000.0,
                "tax_base_amount": -30000.0,
                "l10n_ge_treaty_exempt_amount": -450.0,
            },
            {
                "tax_line_id": self.tax_dividends.id,
                "amount_currency": -50.0,
                "balance": -150.0,
                "tax_base_amount": -3000.0,
                "l10n_ge_treaty_exempt_amount": 0.0,
            },
        ])
        other_lines = payment.move_id.line_ids - withholding_tax_lines
        self.assertFalse(any(other_lines.mapped("l10n_ge_treaty_exempt_amount")))

    def test_treaty_exempt_amount_on_refund_payment(self):
        """ On the payment of a credit note, the treaty exempt amount follows the sign of the base amount. """
        credit_note = self._create_invoice_one_line(move_type="in_refund", price_unit=1000.0, post=True)
        payment = self._register_payment_with_withholding(credit_note, [
            {"tax_id": self.tax_services.id, "base_amount": 1000.0, "l10n_ge_treaty_exempt_amount": 40.0},
        ])
        self.assertRecordValues(payment.move_id.line_ids.filtered("tax_line_id"), [{
            "balance": 100.0,
            "tax_base_amount": 1000.0,
            "l10n_ge_treaty_exempt_amount": 40.0,
        }])

    def test_treaty_exempt_amount_per_analytic_distribution(self):
        """ Withholding lines of one tax with different analytic distributions give one withholding tax journal
        item each, and each item only carries the treaty exempt amount of its own lines.
        """
        analytic_plan = self.env["account.analytic.plan"].create({"name": "Plan"})
        analytic_account_1, analytic_account_2 = self.env["account.analytic.account"].create([
            {"name": "Account 1", "plan_id": analytic_plan.id},
            {"name": "Account 2", "plan_id": analytic_plan.id},
        ])
        bill = self._create_invoice_one_line(move_type="in_invoice", price_unit=10000.0, post=True)
        payment = self._register_payment_with_withholding(bill, [
            {
                "tax_id": self.tax_services.id,
                "base_amount": 6000.0,
                "l10n_ge_treaty_exempt_amount": 100.0,
                "analytic_distribution": {str(analytic_account_1.id): 100.0},
            },
            {
                "tax_id": self.tax_services.id,
                "base_amount": 4000.0,
                "l10n_ge_treaty_exempt_amount": 50.0,
                "analytic_distribution": {str(analytic_account_2.id): 100.0},
            },
        ])
        self.assertRecordValues(payment.move_id.line_ids.filtered("tax_line_id").sorted("balance"), [
            {
                "balance": -600.0,
                "analytic_distribution": {str(analytic_account_1.id): 100.0},
                "l10n_ge_treaty_exempt_amount": -100.0,
            },
            {
                "balance": -400.0,
                "analytic_distribution": {str(analytic_account_2.id): 100.0},
                "l10n_ge_treaty_exempt_amount": -50.0,
            },
        ])

    def test_zero_withholding_tax_line_kept(self):
        """ A withholding fully exempted by a treaty still gets its withholding tax journal item, at zero,
        with its return grid and treaty exempt amount.
        """
        bill = self._create_invoice_one_line(move_type="in_invoice", price_unit=1000.0, post=True)
        payment = self._register_payment_with_withholding(bill, [
            {"tax_id": self.tax_dividends.id, "base_amount": 1000.0, "amount": 0.0, "l10n_ge_treaty_exempt_amount": 50.0},
        ])
        self.assertRecordValues(payment.move_id.line_ids.filtered("tax_line_id"), [{
            "tax_line_id": self.tax_dividends.id,
            "balance": 0.0,
            "tax_base_amount": -1000.0,
            "tax_tag_ids": self._get_tag("1(T)_W_D").ids,
            "l10n_ge_treaty_exempt_amount": -50.0,
        }])

    def test_withholding_tax_grids(self):
        """ A withholding tax puts its return grids on the base and tax journal items of the payment. """
        bill = self._create_invoice_one_line(move_type="in_invoice", price_unit=1000.0, post=True)
        payment = self._register_payment_with_withholding(bill, [
            {"tax_id": self.tax_dividends.id, "base_amount": 1000.0},
        ])
        lines = payment.move_id.line_ids
        self.assertRecordValues(lines.filtered("tax_ids"), [
            {"balance": 1000.0, "tax_tag_ids": self._get_tag("1(B)_W_D").ids},
        ])
        self.assertRecordValues(lines.filtered("tax_line_id"), [
            {"balance": -50.0, "tax_tag_ids": self._get_tag("1(T)_W_D").ids},
        ])
