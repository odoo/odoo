from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nGeWithholdingGross(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ge")
    def setUpClass(cls):
        super().setUpClass()
        chart_template = cls.env["account.chart.template"].with_company(cls.company_data["company"])
        cls.tax_dividends = chart_template.ref("ge_tax_wh_5_d")
        cls.tax_interest = chart_template.ref("ge_tax_wh_5_i")
        cls.tax_vat = chart_template.ref("ge_vat_purchase_18")

    def test_gross_toggle_recomputes_draft_bills(self):
        """ Turning Gross on a withholding tax recomputes the withholding amounts of the draft bills using it. """
        bill = self._create_invoice_one_line(move_type="in_invoice", price_unit=1000.0, tax_ids=self.tax_dividends.ids)
        self.assertRecordValues(bill, [{
            "withholding_residual_amount_currency": 50.0,
            "l10n_ge_gross_withholding_amount_currency": 0.0,
            "withholding_net_residual_amount_currency": 950.0,
        }])

        self.tax_dividends.l10n_ge_is_gross = True
        self.assertRecordValues(bill, [{
            "withholding_residual_amount_currency": 52.63,
            "l10n_ge_gross_withholding_amount_currency": 52.63,
            "withholding_net_residual_amount_currency": 1000.0,
        }])

    def test_gross_locked_on_posted_bills(self):
        """ Gross can be changed while the tax is only on draft bills, not once a posted bill uses it. """
        bill = self._create_invoice_one_line(move_type="in_invoice", price_unit=1000.0, tax_ids=self.tax_dividends.ids)
        self.assertFalse(self.tax_dividends.l10n_ge_is_gross_locked)
        self.tax_dividends.l10n_ge_is_gross = True
        self.tax_dividends.l10n_ge_is_gross = False

        bill.action_post()
        self.tax_dividends.invalidate_recordset(["l10n_ge_is_gross_locked"])
        self.assertTrue(self.tax_dividends.l10n_ge_is_gross_locked)
        with self.assertRaises(UserError):
            self.tax_dividends.l10n_ge_is_gross = True
        # Writing the current value is not a change.
        self.tax_dividends.l10n_ge_is_gross = False

    def test_gross_only_on_withholding_percentage_tax(self):
        """ Gross is refused on a fixed amount, on a rate of 100% and on a tax that is not a withholding tax. """
        self.tax_dividends.l10n_ge_is_gross = True
        for vals in ({"amount_type": "fixed"}, {"amount": -100.0}, {"is_withholding_tax": False, "amount": 5.0}):
            with self.subTest(vals=vals), self.assertRaises(ValidationError):
                self.tax_dividends.copy(vals)

    def test_gross_withholding_tax_alone_on_line(self):
        """ A gross withholding tax cannot share a line with another withholding tax, but can with VAT. """
        self.tax_dividends.l10n_ge_is_gross = True
        self._create_invoice_one_line(move_type="in_invoice", price_unit=1000.0, tax_ids=(self.tax_dividends + self.tax_vat).ids)
        with self.assertRaises(ValidationError):
            self._create_invoice_one_line(move_type="in_invoice", price_unit=1000.0, tax_ids=(self.tax_dividends + self.tax_interest).ids)

    def test_gross_and_deducted_withholding_on_different_lines(self):
        """ Only the deducted withholding is taken from the vendor. """
        self.tax_dividends.l10n_ge_is_gross = True
        bill = self._create_invoice(move_type="in_invoice", invoice_line_ids=[
            self._prepare_invoice_line(price_unit=1000.0, tax_ids=self.tax_dividends.ids),
            self._prepare_invoice_line(price_unit=2000.0, tax_ids=self.tax_interest.ids),
        ])
        self.assertRecordValues(bill, [{
            "withholding_total_amount_currency": 152.63,
            "l10n_ge_gross_withholding_amount_currency": 52.63,
            "withholding_residual_amount_currency": 152.63,
            "withholding_net_residual_amount_currency": 2900.0,
        }])
