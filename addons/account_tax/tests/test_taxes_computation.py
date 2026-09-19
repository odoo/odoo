from odoo import Command
from odoo.tests import TransactionCase, tagged

from .common import BaseTaxCommon


@tagged("post_install", "-at_install")
class TestBaseTaxComputation(BaseTaxCommon):
    def test_standalone_seams_absent_without_account(self):
        if self.account_installed:
            self.skipTest("account installed: standalone fallbacks not exercised")
        company_fields = self.env["res.company"]._fields
        self.assertNotIn("account_config_id", company_fields)
        tax = self._tax(21.0)
        self.assertFalse(tax.company_price_include)
        self.assertFalse(tax.price_include)
        tax_incl = self._tax(21.0, price_include_override="tax_included")
        self.assertTrue(tax_incl.price_include)

    def test_default_rounding_is_round_per_line_standalone(self):
        if self.account_installed:
            self.skipTest("account installed: company drives the rounding method")
        tax = self._tax(21.0)
        base_line = self._base_line(tax, 21.53, quantity=2.0)
        self.env["account.tax"]._add_tax_details_in_base_line(base_line, self.company)
        tax_data = base_line["tax_details"]["taxes_data"][0]
        self.assertEqual(tax_data["raw_tax_amount"], self.currency.round(43.06 * 0.21))

    def test_compute_all_percent_excluded(self):
        tax = self._tax(21.0)
        res = tax.compute_all(100.0)
        self.assertEqual(res["total_excluded"], 100.0)
        self.assertEqual(res["total_included"], 121.0)
        self.assertEqual(len(res["taxes"]), 1)
        self.assertEqual(res["taxes"][0]["amount"], 21.0)
        self.assertEqual(res["taxes"][0]["base"], 100.0)

    def test_compute_all_percent_included(self):
        tax = self._tax(21.0, price_include_override="tax_included")
        res = tax.compute_all(121.0)
        self.assertEqual(res["total_excluded"], 100.0)
        self.assertEqual(res["total_included"], 121.0)

    def test_compute_all_fixed(self):
        tax = self._tax(5.0, amount_type="fixed")
        res = tax.compute_all(100.0, quantity=3.0)
        self.assertEqual(res["total_included"], 315.0)

    def test_compute_all_fixed_negative_price_flips_sign(self):
        tax = self._tax(5.0, amount_type="fixed")
        res = tax.compute_all(-100.0, quantity=3.0)
        self.assertEqual(res["taxes"][0]["amount"], -15.0)

    def test_compute_all_division(self):
        tax = self._tax(10.0, amount_type="division")
        res = tax.compute_all(200.0)
        self.assertEqual(res["total_included"], 222.22)

    def test_compute_all_group(self):
        child_a = self._tax(21.0)
        child_b = self._tax(10.0, amount_type="division")
        group = self._tax(
            0.0, amount_type="group", children_tax_ids=[(6, 0, (child_a + child_b).ids)]
        )
        res = group.compute_all(100.0)
        self.assertEqual(len(res["taxes"]), 2)
        self.assertEqual(res["total_included"], 132.11)

    def test_compute_all_refund_matches_invoice(self):
        tax = self._tax(21.0)
        self.assertEqual(
            tax.compute_all(100.0, is_refund=True)["total_included"], 121.0
        )

    def test_pipeline_round_per_line_two_lines(self):
        tax = self._tax(21.0, price_include_override="tax_included")
        base_lines = [self._base_line(tax, 21.53) for _ in range(2)]
        Tax = self.env["account.tax"]
        for base_line in base_lines:
            Tax._add_tax_details_in_base_line(
                base_line, self.company, rounding_method="round_per_line"
            )
        Tax._round_base_lines_tax_details(base_lines, self.company)
        totals = Tax._get_tax_totals_summary(base_lines, self.currency, self.company)
        self.assertAlmostEqual(totals["base_amount"], 35.58, places=2)
        self.assertAlmostEqual(totals["tax_amount"], 7.48, places=2)
        self.assertAlmostEqual(totals["total_amount"], 43.06, places=2)

    def test_pipeline_round_globally_distributes_delta(self):
        tax = self._tax(21.0, price_include_override="tax_included")
        base_lines = [self._base_line(tax, 21.53) for _ in range(2)]
        Tax = self.env["account.tax"]
        for base_line in base_lines:
            Tax._add_tax_details_in_base_line(
                base_line, self.company, rounding_method="round_globally"
            )
        Tax._round_base_lines_tax_details(base_lines, self.company)
        totals = Tax._get_tax_totals_summary(base_lines, self.currency, self.company)
        self.assertAlmostEqual(totals["base_amount"], 35.59, places=2)
        self.assertAlmostEqual(totals["tax_amount"], 7.47, places=2)
        self.assertAlmostEqual(totals["total_amount"], 43.06, places=2)
        self.assertTrue(totals["same_tax_base"])
        deltas = sorted(
            round(base_line["tax_details"]["delta_total_excluded"], 2)
            for base_line in base_lines
        )
        self.assertEqual(deltas, [0.0, 0.01])

    def test_import_extra_tax_data_keeps_manual_total_without_taxes(self):
        Tax = self.env["account.tax"]
        base_line = self._base_line(Tax, price_unit=100.0, manual_total_excluded=-50.0)
        extra_tax_data = Tax._export_base_line_extra_tax_data(base_line)
        self.assertNotIn("manual_tax_amounts", extra_tax_data)
        self.assertEqual(extra_tax_data.get("manual_total_excluded"), -50.0)
        imported = Tax._import_base_line_extra_tax_data(base_line, extra_tax_data)
        self.assertEqual(imported.get("manual_total_excluded"), -50.0)

    def test_adapt_price_unit_to_another_taxes(self):
        src = self._tax(6.0, price_include_override="tax_included")
        dst = self._tax(21.0, price_include_override="tax_included")
        adapted = self.env["account.tax"]._adapt_price_unit_to_another_taxes(
            106.0, None, src, dst
        )
        self.assertEqual(round(adapted, 4), 121.0)


@tagged("post_install", "-at_install")
class TestBaseTaxRepartitionViews(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        if not cls.company.country_id:
            cls.company.country_id = cls.env.ref("base.us")
        cls.tax_group = cls.env["account.tax.group"].create(
            {
                "name": "repartition views group",
                "company_ids": [Command.set(cls.company.ids)],
            }
        )

    def _tax(self):
        return self.env["account.tax"].create(
            {
                "name": "repartition views",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "tax_group_id": self.tax_group.id,
                "company_ids": [Command.set(self.company.ids)],
                "country_id": self.company.country_id.id,
            }
        )

    def _replacement(self, tax_lines=1):
        from odoo import Command

        return [Command.clear(), Command.create({"repartition_type": "base"})] + [
            Command.create(
                {"repartition_type": "tax", "factor_percent": 100.0 / tax_lines}
            )
            for _ in range(tax_lines)
        ]

    def _kinds(self, tax):
        tax.invalidate_recordset()
        return sorted(
            (line.document_type, line.repartition_type)
            for line in tax.repartition_line_ids
        )

    def test_replacing_one_view_leaves_the_other_alone(self):
        tax = self._tax()
        untouched = tax.refund_repartition_line_ids
        self.assertTrue(untouched)

        tax.write({"invoice_repartition_line_ids": self._replacement()})

        self.assertEqual(
            tax.refund_repartition_line_ids,
            untouched,
            "clearing the invoice distribution removed the refund one",
        )
        self.assertEqual(len(tax.invoice_repartition_line_ids), 2)

    def test_replacing_both_views_in_one_write(self):
        tax = self._tax()

        tax.write(
            {
                "invoice_repartition_line_ids": self._replacement(tax_lines=2),
                "refund_repartition_line_ids": self._replacement(tax_lines=2),
            }
        )

        self.assertEqual(len(tax.invoice_repartition_line_ids), 3)
        self.assertEqual(len(tax.refund_repartition_line_ids), 3)
        self.assertEqual(
            self._kinds(tax),
            [
                ("invoice", "base"),
                ("invoice", "tax"),
                ("invoice", "tax"),
                ("refund", "base"),
                ("refund", "tax"),
                ("refund", "tax"),
            ],
        )

    def test_set_command_keeps_the_other_view(self):
        from odoo import Command

        tax = self._tax()
        keep = tax.invoice_repartition_line_ids
        refund_before = tax.refund_repartition_line_ids

        tax.write({"invoice_repartition_line_ids": [Command.set(keep.ids)]})

        self.assertEqual(tax.invoice_repartition_line_ids, keep)
        self.assertEqual(tax.refund_repartition_line_ids, refund_before)
