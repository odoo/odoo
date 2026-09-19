from odoo.tests import tagged

from .common import BaseTaxCommon


@tagged("post_install", "-at_install")
class TestTaxRoundingFromTaxLines(BaseTaxCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.account_installed:
            cls.company.account_config_id.tax_calculation_rounding_method = (
                "round_per_line"
            )
        cls.tax = cls._tax(21.0, price_include_override="tax_included")
        cls.tax_rep = cls.tax.invoice_repartition_line_ids.filtered(
            lambda rep: rep.repartition_type == "tax"
        )[0]

    def _rounded_lines(self, tax_lines=None, price_unit=21.53, count=2):
        AccountTax = self.env["account.tax"]
        base_lines = [self._base_line(self.tax, price_unit) for _ in range(count)]
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company)
        AccountTax._round_base_lines_tax_details(
            base_lines, self.company, tax_lines=tax_lines
        )
        return base_lines

    def _total_tax(self, base_lines):
        return sum(
            tax_data["tax_amount_currency"]
            for base_line in base_lines
            for tax_data in base_line["tax_details"]["taxes_data"]
        )

    def _tax_line(self, amount, tax_rep=None, sign=1):
        return {
            "tax_repartition_line_id": tax_rep or self.tax_rep,
            "sign": sign,
            "currency_id": self.currency,
            "amount_currency": amount,
            "balance": amount,
        }

    def test_without_tax_lines_the_computed_amounts_stand(self):
        base_lines = self._rounded_lines()
        self.assertEqual(
            [line["tax_details"]["total_excluded_currency"] for line in base_lines],
            [17.79, 17.79],
        )
        self.assertEqual(self._total_tax(base_lines), 7.48)

    def test_round_globally_moves_the_total_by_a_cent(self):
        if not self.account_installed:
            self.skipTest("no company rounding-method field without account")
        self.company.account_config_id.tax_calculation_rounding_method = (
            "round_globally"
        )
        base_lines = self._rounded_lines()
        self.assertAlmostEqual(self._total_tax(base_lines), 7.47, places=2)

    def test_tax_lines_agreeing_with_the_computation_change_nothing(self):
        base_lines = self._rounded_lines(tax_lines=[self._tax_line(7.48)])
        self.assertEqual(self._total_tax(base_lines), 7.48)

    def test_a_higher_tax_line_pulls_the_total_up_to_it(self):
        base_lines = self._rounded_lines(tax_lines=[self._tax_line(7.50)])
        self.assertEqual(self._total_tax(base_lines), 7.50)

    def test_a_lower_tax_line_pulls_the_total_down_to_it(self):
        base_lines = self._rounded_lines(tax_lines=[self._tax_line(7.40)])
        self.assertEqual(self._total_tax(base_lines), 7.40)

    def test_no_tax_lines_at_all_is_a_no_op(self):
        base_lines = self._rounded_lines(tax_lines=None)
        self.assertEqual(self._total_tax(base_lines), 7.48)

    def test_an_empty_tax_line_list_is_a_no_op(self):
        base_lines = self._rounded_lines(tax_lines=[])
        self.assertEqual(self._total_tax(base_lines), 7.48)

    def test_a_tax_line_of_another_tax_is_ignored(self):
        other_tax = self._tax(7.0)
        other_rep = other_tax.invoice_repartition_line_ids.filtered(
            lambda rep: rep.repartition_type == "tax"
        )[0]
        base_lines = self._rounded_lines(
            tax_lines=[self._tax_line(99.0, tax_rep=other_rep)]
        )
        self.assertEqual(self._total_tax(base_lines), 7.48)

    def test_several_tax_lines_of_one_tax_are_summed_before_adjusting(self):
        base_lines = self._rounded_lines(
            tax_lines=[self._tax_line(4.00), self._tax_line(3.50)]
        )
        self.assertEqual(self._total_tax(base_lines), 7.50)

    def test_an_opposite_signed_tax_line_subtracts(self):
        base_lines = self._rounded_lines(
            tax_lines=[self._tax_line(7.50), self._tax_line(0.10, sign=-1)]
        )
        self.assertEqual(self._total_tax(base_lines), 7.40)
