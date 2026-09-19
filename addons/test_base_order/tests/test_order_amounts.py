from odoo.tests import tagged

from .common import BaseOrderTestCase


@tagged("post_install", "-at_install")
class TestOrderAmounts(BaseOrderTestCase):
    """`mixin.order.amount`: the order-level rollup and the credit warning.

    `base_order`'s own amount tests build a `sale.order`, so they assert
    sale's behaviour; these run against the mixin through the model that
    carries nothing else.
    """

    def _line(self, order, qty=1.0, price=100.0, invoiced=0.0):
        return self._make_line(
            order=order,
            product_qty=qty,
            price_unit=price,
            qty_invoiced_input=invoiced,
        )

    # ─── the rollup ───────────────────────────────────────────────

    def test_untaxed_total_sums_the_line_subtotals(self):
        order = self._make_order()
        self._line(order, qty=2.0, price=100.0)
        self._line(order, qty=1.0, price=50.0)

        self.assertAlmostEqual(order.amount_untaxed, 250.0, places=2)

    def test_total_is_untaxed_plus_tax(self):
        order = self._make_order()
        self._line(order, qty=2.0, price=100.0)

        self.assertAlmostEqual(
            order.amount_total,
            order.amount_untaxed + order.amount_tax,
            places=2,
        )

    def test_an_order_without_lines_is_worth_nothing(self):
        order = self._make_order()

        self.assertAlmostEqual(order.amount_untaxed, 0.0, places=2)
        self.assertAlmostEqual(order.amount_tax, 0.0, places=2)
        self.assertAlmostEqual(order.amount_total, 0.0, places=2)

    def test_a_display_line_adds_nothing_to_the_total(self):
        order = self._make_order()
        self._line(order, qty=2.0, price=100.0)
        self.env["base.order.test.line"].create(
            {
                "order_id": order.id,
                "display_type": "line_section",
                "name": "A section",
            }
        )

        self.assertAlmostEqual(order.amount_untaxed, 200.0, places=2)

    def test_the_total_follows_a_line_being_removed(self):
        order = self._make_order()
        first = self._line(order, qty=1.0, price=100.0)
        self._line(order, qty=1.0, price=50.0)
        self.assertAlmostEqual(order.amount_untaxed, 150.0, places=2)

        first.unlink()

        self.assertAlmostEqual(order.amount_untaxed, 50.0, places=2)

    # ─── the invoiced rollup ──────────────────────────────────────

    def test_invoiced_and_uninvoiced_amounts_split_the_order(self):
        order = self._make_order()
        self._line(order, qty=4.0, price=100.0, invoiced=1.0)
        self._line(order, qty=2.0, price=50.0, invoiced=2.0)

        self.assertAlmostEqual(order.amount_taxexc_invoiced, 200.0, places=2)
        self.assertAlmostEqual(order.amount_taxexc_to_invoice, 300.0, places=2)
        self.assertAlmostEqual(
            order.amount_taxexc_invoiced + order.amount_taxexc_to_invoice,
            order.amount_untaxed,
            places=2,
        )

    def test_nothing_invoiced_leaves_the_whole_order_to_invoice(self):
        order = self._make_order()
        self._line(order, qty=2.0, price=100.0)

        self.assertAlmostEqual(order.amount_taxexc_invoiced, 0.0, places=2)
        self.assertAlmostEqual(order.amount_taxexc_to_invoice, 200.0, places=2)

    # ─── the credit warning ───────────────────────────────────────

    def test_a_partner_over_its_credit_limit_warns_on_a_draft_order(self):
        company = self.env.company
        company.account_config_id.account_use_credit_limit = True
        self.partner.credit_limit = 1.0
        order = self._make_order()
        self._line(order, qty=1.0, price=500.0)

        self.assertTrue(order.partner_credit_warning)
        self.assertIn(self.partner.name, order.partner_credit_warning)

    def test_no_warning_when_the_company_does_not_use_credit_limits(self):
        self.env.company.account_config_id.account_use_credit_limit = False
        self.partner.credit_limit = 1.0
        order = self._make_order()
        self._line(order, qty=1.0, price=500.0)

        self.assertFalse(order.partner_credit_warning)

    def test_no_warning_once_the_order_leaves_draft(self):
        """The warning is advice before committing, not a standing flag."""
        self.env.company.account_config_id.account_use_credit_limit = True
        self.partner.credit_limit = 1.0
        order = self._make_order()
        self._line(order, qty=1.0, price=500.0)
        self.assertTrue(order.partner_credit_warning)

        order.action_confirm()
        order.invalidate_recordset()

        self.assertFalse(order.partner_credit_warning)
