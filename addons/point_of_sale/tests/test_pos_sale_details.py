import logging
from datetime import timedelta

from lxml import html as lxml_html

import odoo
from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import new_test_user

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

_logger = logging.getLogger(__name__)


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSaleDetails(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.report = self.env["report.point_of_sale.report_saledetails"]

    def _create_order(self, session, product, amount):
        return self.env["pos.order"].create(
            {
                "company_id": self.env.company.id,
                "session_id": session.id,
                "partner_id": self.partner_a.id,
                "lines": [
                    (
                        0,
                        0,
                        {
                            "name": "OL/0001",
                            "product_id": product.id,
                            "price_unit": amount,
                            "discount": 0,
                            "qty": 1,
                            "tax_ids": [],
                            "price_subtotal": amount,
                            "price_subtotal_incl": amount,
                        },
                    )
                ],
                "pricelist_id": self.config.pricelist_id.id,
                "amount_paid": amount,
                "amount_total": amount,
                "amount_tax": 0.0,
                "amount_return": 0.0,
                "last_order_preparation_change": "{}",
                "to_invoice": False,
            }
        )

    def test_closing_difference_found_in_translated_database(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        product = self.create_product("Product A", self.categ_basic, 100)

        self.config.open_ui()
        session = self.config.current_session_id
        order = self._create_order(session, product, 100)
        self.make_payment(order, self.bank_split_pm1, 100)

        session.with_context(lang="fr_FR").action_pos_session_closing_control(
            bank_payment_method_diffs={self.bank_split_pm1.id: -20}
        )

        diff_move = self.env["account.move"].search(
            [("ref", "=like", "Différence de clôture%")]
        )
        self.assertTrue(
            diff_move,
            "the closing difference move should be referenced in French",
        )

        report = self.report.with_context(lang="fr_FR").get_sale_details(
            session_ids=[session.id]
        )
        row = next(
            p for p in report["payments"] if p.get("id") == self.bank_split_pm1.id
        )
        self.assertTrue(
            row["count"],
            "the report must locate the difference move in a French database",
        )
        self.assertEqual(row["money_difference"], -20)

    def test_cash_difference_line_excluded_not_oldest_move(self):
        cash_journal = self.cash_pm1.journal_id
        cash_journal.loss_account_id = self.company_data["default_account_expense"]
        cash_journal.profit_account_id = self.company_data["default_account_revenue"]
        self.config.cash_control = True
        product = self.create_product("Product A", self.categ_basic, 100)

        self.config.open_ui()
        session1 = self.config.current_session_id
        session1.set_opening_control(0, None)
        session1.try_cash_in_out("in", 200, "Float", False, {"translatedType": "in"})
        session1.update_closing_cash_details(200)
        session1.close_session_from_ui()

        self.config.open_ui()
        session2 = self.config.current_session_id
        session2.set_opening_control(200, None)
        order = self._create_order(session2, product, 100)
        self.make_payment(order, self.bank_pm1, 100)
        session2.try_cash_in_out(
            "out", 50, "Cash out", False, {"translatedType": "out"}
        )
        session2.update_closing_cash_details(142)
        session2.close_session_from_ui()

        report = self.report.get_sale_details(session_ids=[session2.id])
        cash_row = next(p for p in report["payments"] if not p.get("id"))
        amounts = [move["amount"] for move in cash_row["cash_moves"]]

        self.assertIn(-50, amounts, "the genuine cash out must be reported")
        self.assertNotIn(
            -8,
            amounts,
            "the counting difference must not be listed as a cash movement",
        )

    def test_open_session_included_in_date_window(self):
        product = self.create_product("Product A", self.categ_basic, 100)
        self.config.open_ui()
        session = self.config.current_session_id
        session.set_opening_control(0, None)
        order = self._create_order(session, product, 100)
        self.make_payment(order, self.bank_pm1, 100)

        now = fields.Datetime.now()
        report = self.report.get_sale_details(
            date_start=fields.Datetime.to_string(now - timedelta(hours=1)),
            date_stop=fields.Datetime.to_string(now + timedelta(hours=1)),
            config_ids=self.config.ids,
        )
        self.assertEqual(
            report["session_name"],
            session.name,
            "an open session (stop_at NULL) must not be filtered out",
        )

    def test_straddling_session_included_in_date_window(self):
        product = self.create_product("Product A", self.categ_basic, 100)
        self.config.open_ui()
        session = self.config.current_session_id
        session.set_opening_control(0, None)
        order = self._create_order(session, product, 100)
        self.make_payment(order, self.bank_pm1, 100)
        session.action_pos_session_closing_control()

        now = fields.Datetime.now()
        window_start = now - timedelta(hours=1)
        session.sudo().start_at = window_start - timedelta(hours=10)

        report = self.report.get_sale_details(
            date_start=fields.Datetime.to_string(window_start),
            date_stop=fields.Datetime.to_string(now + timedelta(hours=1)),
            config_ids=self.config.ids,
        )
        self.assertEqual(
            report["session_name"],
            session.name,
            "a session straddling the window start must not be filtered out",
        )


@odoo.tests.tagged("post_install", "-at_install")
class TestPosCategoryGuards(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def test_check_hour_rejects_window_that_never_opens(self):
        category = self.env["pos.category"].create({"name": "Snacks"})

        with self.assertRaises(ValidationError):
            category.write({"hour_after": 10.0, "hour_until": 0.0})

        with self.assertRaises(ValidationError):
            self.env["pos.category"].create(
                {"name": "Drinks", "hour_after": 10.0, "hour_until": 0.0}
            )

        with self.assertRaises(ValidationError):
            category.write({"hour_until": 25.0})

        category.write({"hour_after": 0.0, "hour_until": 24.0})
        self.assertEqual(category.hour_until, 24.0)

    def test_unlink_ignores_session_that_cannot_show_the_category(self):
        category = self.env["pos.category"].create({"name": "Snacks"})
        other_category = self.env["pos.category"].create({"name": "Drinks"})
        self.config.write(
            {
                "limit_categories": True,
                "iface_available_categ_ids": [(6, 0, other_category.ids)],
            }
        )
        self.config.open_ui()

        category.unlink()
        self.assertFalse(category.exists())

    def test_unlink_blocked_by_session_that_shows_the_category(self):
        category = self.env["pos.category"].create({"name": "Snacks"})
        self.config.write(
            {
                "limit_categories": True,
                "iface_available_categ_ids": [(6, 0, category.ids)],
            }
        )
        self.config.open_ui()
        session = self.config.current_session_id

        with self.assertRaisesRegex(UserError, session.name):
            category.unlink()

    def test_unlink_ignores_session_of_another_company(self):
        category = self.env["pos.category"].create({"name": "Snacks"})
        self.config.open_ui()
        other_company = self.setup_other_company()["company"]

        category.with_context(allowed_company_ids=other_company.ids).unlink()
        self.assertFalse(category.exists())


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSaleDetailsCoherence(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.report = self.env["report.point_of_sale.report_saledetails"]

    def _order(self, session, product, price, qty=1, taxes=None):
        return self.env["pos.order"].create(
            {
                "company_id": self.env.company.id,
                "session_id": session.id,
                "partner_id": self.partner_a.id,
                "lines": [
                    (
                        0,
                        0,
                        {
                            "name": "OL/0001",
                            "product_id": product.id,
                            "price_unit": price,
                            "discount": 0,
                            "qty": qty,
                            "tax_ids": [(6, 0, taxes or [])],
                            "price_subtotal": price * qty,
                            "price_subtotal_incl": price * qty,
                        },
                    )
                ],
                "pricelist_id": self.config.pricelist_id.id,
                "amount_paid": price * qty,
                "amount_total": price * qty,
                "amount_tax": 0.0,
                "amount_return": 0.0,
                "last_order_preparation_change": "{}",
                "to_invoice": False,
            }
        )

    def _open_session(self):
        self.config.open_ui()
        session = self.config.current_session_id
        session.set_opening_control(0, None)
        return session

    def test_every_base_in_the_report_is_computed_from_the_line(self):
        tax = self.env["account.tax"].create({"name": "Coherence 10%", "amount": 10})
        product = self.create_product("Taxed", self.categ_basic, 100, tax_ids=tax.ids)
        session = self._open_session()
        order = self._order(session, product, 100, taxes=tax.ids)
        self.make_payment(order, self.bank_pm1, order.amount_total)
        order.lines.sudo().price_subtotal = 1.0

        report = self.report.get_sale_details(session_ids=[session.id])
        self.assertEqual(
            report["taxes"],
            [
                {
                    "id": tax.id,
                    "name": tax.name,
                    "tax_amount": 10.0,
                    "base_amount": 100.0,
                }
            ],
        )
        self.assertEqual(
            report["taxes_info"],
            {"tax_amount": 10.0, "base_amount": 100.0},
            "the tax total must be computed the way the tax rows above it are",
        )
        self.assertEqual(
            report["products_info"]["total"],
            report["taxes_info"]["base_amount"],
            "the products block and the tax block report one untaxed total",
        )

    def test_refund_block_reads_in_one_direction(self):
        tax = self.env["account.tax"].create({"name": "Refund 10%", "amount": 10})
        product = self.create_product(
            "Returned", self.categ_basic, 100, tax_ids=tax.ids
        )
        session = self._open_session()
        order = self._order(session, product, 100, taxes=tax.ids)
        self.make_payment(order, self.bank_pm1, 110)
        refund = order._refund()
        self.make_payment(refund, self.bank_pm1, -110)

        report = self.report.get_sale_details(session_ids=[session.id])
        rows = [
            row
            for category in report["refund_products"]
            for row in category["products"]
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["quantity"], 1.0)
        self.assertEqual(row["base_amount"], 100.0)
        self.assertGreater(row["total_paid"], 0.0)
        self.assertEqual(report["refund_info"]["total"], 100.0)
        self.assertEqual(report["refund_taxes_info"]["base_amount"], 100.0)
        self.assertEqual(report["refund_taxes_info"]["tax_amount"], 10.0)
        self.assertEqual(
            report["refund_taxes_info"]["base_amount"],
            sum(r["base_amount"] for r in report["refund_taxes"]),
        )

    def test_scope_without_config_or_session_covers_the_window(self):
        product = self.create_product("Scoped", self.categ_basic, 100)
        session = self._open_session()
        order = self._order(session, product, 100)
        self.make_payment(order, self.cash_pm1, 100)

        report = self.report.get_sale_details()
        self.assertEqual(report["nbr_orders"], 1)
        self.assertIn(
            self.config.name,
            report["config_names"],
            "a report that found the order must name the config that took it",
        )
        self.assertTrue(
            all(payment["count"] for payment in report["payments"]),
            "an in-scope session's payments must be counted, not left unclosed",
        )
        self.assertEqual(report["total_paid"], 100.0)

    def test_config_is_named_once_per_config_not_once_per_session(self):
        product = self.create_product("Repeated", self.categ_basic, 100)
        session_ids = []
        for _index in range(3):
            session = self._open_session()
            order = self._order(session, product, 100)
            self.make_payment(order, self.cash_pm1, 100)
            session.update_closing_cash_details(100)
            session.close_session_from_ui()
            session_ids.append(session.id)

        report = self.report.get_sale_details(session_ids=session_ids)
        self.assertEqual(report["config_names"], [self.config.name])

    def test_total_paid_covers_the_same_window_as_the_orders(self):
        product = self.create_product("Windowed", self.categ_basic, 100)
        session = self._open_session()
        inside = self._order(session, product, 100)
        self.make_payment(inside, self.cash_pm1, 100)
        outside = self._order(session, product, 250)
        self.make_payment(outside, self.bank_pm1, 250)
        outside.sudo().date_order = fields.Datetime.now() - timedelta(days=5)

        now = fields.Datetime.now()
        report = self.report.get_sale_details(
            fields.Datetime.to_string(now - timedelta(hours=1)),
            fields.Datetime.to_string(now + timedelta(hours=1)),
            self.config.ids,
        )
        self.assertEqual(report["nbr_orders"], 1)
        self.assertEqual(
            report["total_paid"],
            report["currency"]["total_paid"],
            "payments and order totals must be read over the same window",
        )

    def test_combo_label_does_not_travel_to_a_plain_line(self):
        combo_part = self.create_product("Side", self.categ_basic, 0)
        product = self.create_product("Meal", self.categ_basic, 100)
        session = self._open_session()
        plain = self._order(session, product, 100)
        self.make_payment(plain, self.cash_pm1, 100)
        with_combo = self._order(session, product, 100)
        self.env["pos.order.line"].create(
            {
                "order_id": with_combo.id,
                "product_id": combo_part.id,
                "qty": 1,
                "price_unit": 0,
                "price_subtotal": 0,
                "price_subtotal_incl": 0,
                "name": "combo child",
                "combo_parent_id": with_combo.lines[0].id,
            }
        )
        self.make_payment(with_combo, self.cash_pm1, 100)

        report = self.report.get_sale_details(session_ids=[session.id])
        rows = [
            row
            for category in report["products"]
            for row in category["products"]
            if row["product_name"] == "Meal"
        ]
        labelled = [row for row in rows if row["combo_products_label"]]
        self.assertEqual(
            [row["quantity"] for row in labelled],
            [1.0],
            "only the unit actually sold as a combo may carry the combo label",
        )
        self.assertEqual(sum(row["quantity"] for row in rows), 2.0)

    def test_extra_arguments_do_not_break_the_advertised_signature(self):
        product = self.create_product("Extra", self.categ_basic, 100)
        session = self._open_session()
        order = self._order(session, product, 100)
        self.make_payment(order, self.cash_pm1, 100)

        report = self.report.get_sale_details(
            session_ids=[session.id], employee_id=False
        )
        self.assertEqual(report["nbr_orders"], 1)

    def test_window_covers_the_last_second_of_the_day(self):
        date_start, date_stop = self.report._get_date_start_and_date_stop(False, False)
        self.assertEqual(
            date_stop - date_start,
            timedelta(days=1, microseconds=-1),
            "an order timed at 23:59:59.5 belongs to the day it was taken",
        )

    def test_unrelated_move_with_a_matching_ref_is_not_a_difference(self):
        product = self.create_product("Unrelated", self.categ_basic, 100)
        session = self._open_session()
        order = self._order(session, product, 100)
        self.make_payment(order, self.bank_pm1, 100)
        session.action_pos_session_closing_control()

        ref = session._get_diff_account_move_ref(self.bank_pm1)
        self.env["account.move"].search([("ref", "=", ref)]).unlink()
        self.env["account.move"].create(
            {
                "move_type": "entry",
                "ref": ref,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": self.company_data[
                                "default_account_receivable"
                            ].id,
                            "debit": 40.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": self.company_data[
                                "default_account_payable"
                            ].id,
                            "credit": 40.0,
                        },
                    ),
                ],
            }
        )

        report = self.report.get_sale_details(session_ids=[session.id])
        row = next(p for p in report["payments"] if p.get("id") == self.bank_pm1.id)
        self.assertEqual(row["final_count"], 100.0)
        self.assertEqual(
            row["money_counted"],
            100.0,
            "what was counted is what settled the payments, not the total of a "
            "journal entry that merely shares the closing-difference reference",
        )
        self.assertEqual(row["money_difference"], 0.0)

    def test_a_deduction_line_is_subtracted_not_added(self):
        tax = self.env["account.tax"].create({"name": "Deduction 10%", "amount": 10})
        product = self.create_product(
            "Deducted", self.categ_basic, 100, tax_ids=tax.ids
        )
        session = self._open_session()
        sold = self._order(session, product, 100, qty=2, taxes=tax.ids)
        self.make_payment(sold, self.cash_pm1, sold.amount_total)
        deduction = self._order(session, product, 100, qty=-1, taxes=tax.ids)
        self.assertFalse(deduction.is_refund)
        self.make_payment(deduction, self.cash_pm1, deduction.amount_total)

        report = self.report.get_sale_details(session_ids=[session.id])
        self.assertFalse(report["refund_products"], "a deduction is not a refund")
        rows = [row for c in report["products"] for row in c["products"]]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quantity"], 1.0)
        self.assertEqual(rows[0]["total_paid"], 100.0)
        self.assertEqual(rows[0]["base_amount"], 100.0)
        self.assertEqual(report["products_info"], {"total": 100.0, "qty": 1.0})
        self.assertEqual(
            report["taxes_info"], {"tax_amount": 10.0, "base_amount": 100.0}
        )

    def test_a_started_session_without_sales_is_still_in_scope(self):
        product = self.create_product("Elsewhere", self.categ_basic, 100)
        quiet_journal = self.cash_pm1.journal_id.copy(
            {"name": "Quiet Cash", "code": "QUIET"}
        )
        quiet_method = self.cash_pm1.copy(
            {
                "name": "Quiet Cash",
                "journal_id": quiet_journal.id,
                "config_ids": [fields.Command.clear()],
            }
        )
        quiet_config = self.env["pos.config"].create(
            {
                "name": "Quiet Shop",
                "payment_method_ids": [fields.Command.set(quiet_method.ids)],
            }
        )
        quiet_config.open_ui()
        quiet_config.current_session_id.set_opening_control(0, None)
        self.assertTrue(quiet_config.current_session_id.cash_journal_id)
        session = self._open_session()
        order = self._order(session, product, 100)
        self.make_payment(order, self.cash_pm1, 100)

        report = self.report.get_sale_details()
        self.assertEqual(report["nbr_orders"], 1)
        self.assertIn("Quiet Shop", report["config_names"])
        self.assertIn(
            quiet_config.current_session_id.id,
            [payment["session"] for payment in report["payments"]],
            "the quiet session must get its uncounted cash row",
        )

    def _count_session_selects(self, run):
        seen = []
        cursor_class = type(self.env.cr)
        original = cursor_class.execute

        def record(cr, query, params=None, *args, **kwargs):
            seen.append(str(query))
            return original(cr, query, params, *args, **kwargs)

        self.patch(cursor_class, "execute", record)
        run()
        return len([q for q in seen if 'FROM "pos_session"' in q])

    def test_drawer_queries_do_not_grow_per_session(self):
        product = self.create_product("Historic", self.categ_basic, 100)
        session_ids = []
        for _index in range(6):
            session = self._open_session()
            order = self._order(session, product, 100)
            self.make_payment(order, self.bank_pm1, 100)
            session.update_closing_cash_details(0)
            session.close_session_from_ui()
            session_ids.append(session.id)

        self.env.invalidate_all()
        two = self._count_session_selects(
            lambda: self.report.get_sale_details(session_ids=session_ids[:2])
        )
        self.env.invalidate_all()
        six = self._count_session_selects(
            lambda: self.report.get_sale_details(session_ids=session_ids)
        )
        report = self.report.get_sale_details(session_ids=session_ids)
        self.assertEqual(
            len([row for row in report["payments"] if not row["id"]]),
            6,
            "each session still gets its own uncounted cash row",
        )
        self.assertEqual(
            six,
            two,
            "reporting three times as many sessions must not take more "
            f"pos_session queries: 2 sessions took {two}, 6 took {six}",
        )

    def test_discounts_are_counted_in_the_pass_that_reads_the_lines(self):
        product = self.create_product("Marked Down", self.categ_basic, 100)
        session = self._open_session()
        discounted = self._order(session, product, 100, qty=2)
        discounted.lines.discount = 25
        discounted.lines._onchange_amount_line_all()
        self.make_payment(discounted, self.cash_pm1, discounted.amount_total)
        plain = self._order(session, product, 100)
        self.make_payment(plain, self.cash_pm1, plain.amount_total)

        report = self.report.get_sale_details(session_ids=[session.id])
        self.assertEqual(
            report["discount_number"], 1, "one of the two orders carries a discount"
        )
        self.assertEqual(report["discount_amount"], 50.0)

    def test_a_matching_ref_in_another_journal_is_a_different_entry(self):
        product = self.create_product("Journals", self.categ_basic, 100)
        session = self._open_session()
        order = self._order(session, product, 100)
        self.make_payment(order, self.bank_pm1, 100)
        session.action_pos_session_closing_control()

        ref = session._get_diff_account_move_ref(self.bank_pm1)
        self.env["account.move"].search([("ref", "=", ref)]).unlink()
        other_journal = self.env["account.journal"].search(
            [("id", "!=", self.bank_pm1.journal_id.id), ("type", "=", "general")],
            limit=1,
        )
        self.assertTrue(other_journal, "the fixture needs a second journal")
        self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": other_journal.id,
                "ref": ref,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": self.bank_pm1.journal_id.loss_account_id.id
                            or self.company_data["default_account_expense"].id,
                            "debit": 70.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": self.company_data[
                                "default_account_receivable"
                            ].id,
                            "credit": 70.0,
                        },
                    ),
                ],
            }
        )

        report = self.report.get_sale_details(session_ids=[session.id])
        row = next(p for p in report["payments"] if p.get("id") == self.bank_pm1.id)
        self.assertNotEqual(
            row.get("money_difference"),
            -70.0,
            "an entry in another journal is not this payment method's difference",
        )
        self.assertEqual(row["money_counted"], 100.0)
        self.assertEqual(row["money_difference"], 0.0)

    def test_two_categories_sharing_a_name_are_two_rows(self):
        first = self.env["pos.category"].create({"name": "Drinks"})
        second = self.env["pos.category"].create({"name": "Drinks"})
        self.assertNotEqual(first.id, second.id)
        cola = self.create_product("Cola", self.categ_basic, 100)
        cola.product_tmpl_id.pos_categ_ids = [(6, 0, first.ids)]
        beer = self.create_product("Beer", self.categ_basic, 100)
        beer.product_tmpl_id.pos_categ_ids = [(6, 0, second.ids)]

        session = self._open_session()
        for product in (cola, beer):
            order = self._order(session, product, 100)
            self.make_payment(order, self.cash_pm1, 100)

        report = self.report.get_sale_details(session_ids=[session.id])
        drinks = [c for c in report["products"] if c["name"] == "Drinks"]
        self.assertEqual(
            len(drinks),
            2,
            "two categories are two rows even when they print the same name",
        )
        self.assertEqual(sorted(c["qty"] for c in drinks), [1.0, 1.0])

    def test_date_report_keeps_requested_dates(self):
        session = self._open_session()
        start = fields.Datetime.now() - timedelta(hours=1)
        stop = start + timedelta(hours=2)

        report = self.report.get_sale_details(start, stop, self.config.ids)

        _logger.debug(
            "Window requested=%s..%s reported=%s..%s",
            start,
            stop,
            report["date_start"],
            report["date_stop"],
        )
        self.assertEqual(report["session_name"], session.name)
        self.assertEqual((report["date_start"], report["date_stop"]), (start, stop))

    def test_session_scope_takes_precedence_over_config(self):
        session = self._open_session()
        other = self.env["pos.config"].create({"name": "Unrelated register"})

        report = self.report.get_sale_details(
            config_ids=other.ids, session_ids=session.ids
        )

        _logger.debug("Explicit session report configs=%s", report["config_names"])
        self.assertEqual(report["config_names"], [session.config_id.name])

    def test_open_cash_movements_and_actual_opening_balance(self):
        product = self.create_product("Cash audit", self.categ_basic, 100)
        self.config.cash_control = True
        self.config.open_ui()
        session = self.config.current_session_id
        session.set_opening_control(75, None)
        self.assertEqual(session.cash_register_balance_start, 75)
        session.try_cash_in_out("in", 20, "Float", False, {"translatedType": "in"})
        session.try_cash_in_out("out", 5, "Supplies", False, {"translatedType": "out"})

        for cash_sale in (False, True):
            with self.subTest(cash_sale=cash_sale):
                if cash_sale:
                    order = self._order(session, product, 100)
                    self.make_payment(order, self.cash_pm1, 100)
                report = self.report.get_sale_details(session_ids=session.ids)
                row = next(row for row in report["payments"] if row["cash"])
                _logger.debug("Open drawer sale=%s row=%s", cash_sale, row)
                self.assertEqual(row["final_count"], 190 if cash_sale else 90)
                self.assertIn(75, [move["amount"] for move in row["cash_moves"]])

    def test_partial_session_does_not_invent_counting_difference(self):
        product = self.create_product("Partial drawer", self.categ_basic, 100)
        session = self._open_session()
        now = fields.Datetime.now()
        for days in (0, -5):
            order = self._order(session, product, 100)
            self.make_payment(order, self.cash_pm1, 100)
            order.date_order = now + timedelta(days=days)
        session.update_closing_cash_details(200)
        session.close_session_from_ui()

        report = self.report.get_sale_details(
            now - timedelta(hours=1), now + timedelta(hours=1), self.config.ids
        )

        _logger.debug("Partial session payments=%s", report["payments"])
        self.assertEqual(report["total_paid"], 100)
        self.assertTrue(report["payments"])
        self.assertFalse(any(row["count"] for row in report["payments"]))
        full = self.report.get_sale_details(session_ids=session.ids)
        cash = next(row for row in full["payments"] if row["cash"])
        self.assertEqual(cash["money_difference"], 0)

    def test_invoice_section_uses_selected_orders(self):
        product = self.create_product("Invoiced service", self.categ_basic, 100)
        product.type = "service"
        session = self._open_session()
        now = fields.Datetime.now()
        inside = self._order(session, product, 100)
        outside = self._order(session, product, 250)
        for order in inside | outside:
            self.make_payment(order, self.bank_pm1, order.amount_total)
            order.action_pos_order_invoice()
        outside.date_order = now - timedelta(days=5)

        report = self.report.get_sale_details(
            now - timedelta(hours=1), now + timedelta(hours=1), self.config.ids
        )

        invoices = [
            row for group in report["invoice_list"] for row in group["invoices"]
        ]
        _logger.debug("Window invoices=%s total=%s", invoices, report["invoice_total"])
        self.assertEqual([row["name"] for row in invoices], [inside.account_move.name])
        self.assertEqual(report["invoice_total"], 100)

    def test_product_totals_use_currency_rounding(self):
        self.env.company.currency_id.rounding = 0.001
        self.env["decimal.precision"].search([("name", "=", "Product Unit")]).digits = 3
        product = self.create_product("Fractional sale", self.categ_basic, 1)
        session = self._open_session()
        order = self._order(session, product, 1, qty=0.125)
        self.assertEqual(order.lines.qty, 0.125)
        self.make_payment(order, self.cash_pm1, order.amount_total)

        report = self.report.get_sale_details(session_ids=session.ids)

        _logger.debug(
            "Three-decimal currency products=%s taxes=%s",
            report["products_info"],
            report["taxes_info"],
        )
        self.assertEqual(report["products_info"]["total"], 0.125)
        self.assertEqual(report["products"][0]["total"], 0.125)
        self.assertEqual(report["taxes_info"]["base_amount"], 0.125)

    def test_challenge_cash_reconciles_before_and_after_close(self):
        self.config.cash_control = True
        self.config.open_ui()
        session = self.config.current_session_id
        session.set_opening_control(75, None)
        product = self.create_product("Drawer challenge", self.categ_basic, 100)
        order = self._order(session, product, 100)
        self.make_payment(order, self.cash_pm1, 100)
        session.try_cash_in_out("in", 20, "Float", False, {"translatedType": "in"})
        session.try_cash_in_out("out", 5, "Supplies", False, {"translatedType": "out"})

        for closed in (False, True):
            with self.subTest(closed=closed):
                if closed:
                    session.update_closing_cash_details(188)
                    session.close_session_from_ui()
                report = self.report.get_sale_details(session_ids=session.ids)
                row = next(row for row in report["payments"] if row["cash"])
                _logger.debug(
                    "CHALLENGE drawer closed=%s model_expected=%s row=%s",
                    closed,
                    session.cash_register_balance_end,
                    row,
                )
                self.assertEqual(session.cash_register_balance_end, 190)
                self.assertEqual(row["final_count"], session.cash_register_balance_end)
                self.assertEqual(
                    [move["amount"] for move in row["cash_moves"]], [75, 20, -5]
                )
                if closed:
                    self.assertEqual(row["money_difference"], -2)

    def test_challenge_difference_survives_language_and_method_rename(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        session = self._open_session()
        product = self.create_product("Renamed method", self.categ_basic, 100)
        order = self._order(session, product, 100)
        self.make_payment(order, self.bank_split_pm1, 100)
        session.with_context(lang="fr_FR").action_pos_session_closing_control(
            bank_payment_method_diffs={self.bank_split_pm1.id: -20}
        )
        self.bank_split_pm1.name = "New terminal name"

        report = self.report.with_context(lang="en_US").get_sale_details(
            session_ids=session.ids
        )

        row = next(
            row for row in report["payments"] if row["id"] == self.bank_split_pm1.id
        )
        _logger.debug("CHALLENGE renamed split method row=%s", row)
        self.assertEqual(row["money_counted"], 80)
        self.assertEqual(row["money_difference"], -20)

    def test_challenge_zero_net_invoices_are_rendered(self):
        product = self.create_product("Offset invoices", self.categ_basic, 100)
        product.type = "service"
        session = self._open_session()
        order = self._order(session, product, 100)
        self.make_payment(order, self.bank_pm1, 100)
        order.action_pos_order_invoice()
        refund = order._refund()
        self.make_payment(refund, self.bank_pm1, -100)
        refund.action_pos_order_invoice()
        data = (
            self.env["pos.daily.sales.reports.wizard"]
            .create({"pos_session_id": session.id})
            ._prepare_report_params()
        )

        report = self.report.get_sale_details(session_ids=session.ids)
        html = self.env["ir.actions.report"]._render_qweb_html(
            "point_of_sale.sale_details_report", [], data=data
        )[0]

        _logger.debug(
            "CHALLENGE offset invoices rows=%s total=%s rendered=%s",
            report["invoice_list"],
            report["invoice_total"],
            b'id="invoices"' in html,
        )
        self.assertEqual(report["invoice_total"], 0)
        self.assertIn(b'id="invoices"', html)
        for move in (order | refund).account_move:
            self.assertIn(move.name.encode(), html)

    def test_challenge_report_denies_public_user(self):
        session = self._open_session()
        with self.assertRaises(AccessError):
            self.report.with_user(self.env.ref("base.public_user")).get_sale_details(
                session_ids=session.ids
            )

    def test_challenge_quiet_closed_drawer_uses_its_own_opening(self):
        self.config.cash_control = True
        self.config.open_ui()
        previous = self.config.current_session_id
        previous.set_opening_control(200, None)
        previous.update_closing_cash_details(200)
        previous.close_session_from_ui()
        self.config.open_ui()
        current = self.config.current_session_id
        current.set_opening_control(75, None)
        current.update_closing_cash_details(75)
        current.close_session_from_ui()

        report = self.report.get_sale_details(session_ids=current.ids)

        row = next(row for row in report["payments"] if row["cash"])
        _logger.debug(
            "CHALLENGE quiet drawer previous=%s opening=%s row=%s",
            previous.cash_register_balance_end_real,
            current.cash_register_balance_start,
            row,
        )
        self.assertEqual(row["final_count"], 75)
        self.assertEqual(row["money_difference"], 0)

    def test_challenge_same_currency_payment_fast_path(self):
        product = self.create_product("Grouped payment", self.categ_basic, 100)
        session = self._open_session()
        orders = self._order(session, product, 100) | self._order(session, product, 100)
        for order in orders:
            self.make_payment(order, self.cash_pm1, 100)
        payments = self.report._get_payment_totals(orders)
        self.env.flush_all()
        orders.invalidate_recordset(["payment_ids"])

        with self.assertQueryCount(0):
            self.report._update_payment_rows_with_report_currency(
                payments, orders, session, session.currency_id
            )

        _logger.debug("CHALLENGE grouped native payments=%s", payments)
        self.assertEqual(sum(row["total"] for row in payments), 200)

    def test_challenge_split_methods_sharing_journal_keep_separate_differences(self):
        other = self.bank_split_pm1.copy({"name": "Second terminal"})
        self.config.payment_method_ids |= other
        session = self._open_session()
        product = self.create_product("Two terminals", self.categ_basic, 200)
        order = self._order(session, product, 200)
        self.make_payment(order, self.bank_split_pm1, 100)
        self.make_payment(order, other, 100)
        session.action_pos_session_closing_control(
            bank_payment_method_diffs={self.bank_split_pm1.id: -20, other.id: 10}
        )
        (self.bank_split_pm1 | other).name = "Same new name"

        report = self.report.get_sale_details(session_ids=session.ids)

        rows = {row["id"]: row for row in report["payments"]}
        _logger.debug("CHALLENGE shared journal rows=%s", rows)
        self.assertEqual(rows[self.bank_split_pm1.id]["money_difference"], -20)
        self.assertEqual(rows[other.id]["money_difference"], 10)

    def test_challenge_legacy_difference_still_resolves(self):
        session = self._open_session()
        product = self.create_product("Legacy difference", self.categ_basic, 100)
        order = self._order(session, product, 100)
        self.make_payment(order, self.bank_split_pm1, 100)
        session.action_pos_session_closing_control(
            bank_payment_method_diffs={self.bank_split_pm1.id: -20}
        )
        move = self.env["account.move"].search(
            [
                ("pos_diff_session_id", "=", session.id),
                ("pos_diff_payment_method_id", "=", self.bank_split_pm1.id),
            ]
        )
        self.assertEqual(len(move), 1)
        move.pos_diff_payment_method_id = False

        for has_session_link in (True, False):
            with self.subTest(has_session_link=has_session_link):
                if not has_session_link:
                    move.pos_diff_session_id = False
                report = self.report.get_sale_details(session_ids=session.ids)
                row = next(
                    row
                    for row in report["payments"]
                    if row["id"] == self.bank_split_pm1.id
                )
                _logger.debug(
                    "CHALLENGE legacy linked=%s row=%s", has_session_link, row
                )
                self.assertEqual(row["money_difference"], -20)

    def test_challenge_manual_expense_is_not_a_counting_difference(self):
        self.config.cash_control = True
        self.config.open_ui()
        session = self.config.current_session_id
        session.set_opening_control(100, None)
        session.try_cash_in_out(
            "out", 5, "Manual expense", False, {"translatedType": "out"}
        )
        movement = session.statement_line_ids
        self.assertEqual(len(movement), 1)
        counterpart = movement.move_id.line_ids.filtered(
            lambda line: line.account_id == session.cash_journal_id.suspense_account_id
        )
        self.assertEqual(len(counterpart), 1)
        counterpart.account_id = session.cash_journal_id.loss_account_id
        session.update_closing_cash_details(95)
        session.close_session_from_ui()

        report = self.report.get_sale_details(session_ids=session.ids)

        row = next(row for row in report["payments"] if row["cash"])
        _logger.debug("CHALLENGE manual loss-account movement row=%s", row)
        self.assertEqual(row["final_count"], 95)
        self.assertEqual(row["money_difference"], 0)
        self.assertEqual([move["amount"] for move in row["cash_moves"]], [100, -5])

    def test_backdated_sales_include_their_session_metadata(self):
        session = self._open_session()
        product = self.create_product("Recovered sale", self.categ_basic, 100)
        order = self._order(session, product, 100)
        self.make_payment(order, self.bank_pm1, 100)
        order.date_order = fields.Datetime.now() - timedelta(days=5)
        start = order.date_order - timedelta(hours=1)
        stop = order.date_order + timedelta(hours=1)

        report = self.report.get_sale_details(start, stop)

        _logger.debug(
            "Recovered sale scope configs=%s session=%s",
            report["config_names"],
            report["session_name"],
        )
        self.assertEqual(report["nbr_orders"], 1)
        self.assertEqual(report["config_names"], [self.config.name])
        self.assertEqual(report["session_name"], session.name)
        self.assertEqual((report["date_start"], report["date_stop"]), (start, stop))

    def test_report_header_uses_selected_company(self):
        company = self.env.company
        company.partner_id.street = "Report origin road"
        other = self.setup_other_company(name="Unrelated current company")["company"]
        other.partner_id.street = "Unrelated header road"
        session = self._open_session()
        report_model = self.report.with_context(
            allowed_company_ids=[other.id, company.id]
        )
        data = (
            self.env["pos.daily.sales.reports.wizard"]
            .create({"pos_session_id": session.id})
            ._prepare_report_params()
        )

        report = report_model.get_sale_details(session_ids=session.ids)
        rendered = (
            self.env["ir.actions.report"]
            .with_context(allowed_company_ids=[other.id, company.id])
            ._render_qweb_html(
                "point_of_sale.sale_details_report",
                [],
                data=data,
            )[0]
        )

        header = (
            lxml_html.fromstring(rendered).xpath('//*[@id="header"]')[0].text_content()
        )
        _logger.debug(
            "Company report current=%s selected=%s header=%s",
            other.name,
            report["company_name"],
            header,
        )
        self.assertEqual(report["company_name"], company.name)
        self.assertIn(company.name, header)
        self.assertIn(company.partner_id.street, header)
        self.assertNotIn(other.partner_id.street, header)

    def test_bank_only_session_has_no_cash_drawer(self):
        self.config.payment_method_ids = self.bank_pm1
        session = self._open_session()
        self.assertFalse(session.cash_journal_id)

        report = self.report.get_sale_details(session_ids=session.ids)

        _logger.debug("Bank-only session rows=%s", report["payments"])
        self.assertFalse(any(row["cash"] for row in report["payments"]))

    def test_legacy_settlement_is_identified_by_reconciliation(self):
        self._assert_legacy_settlement()

    def test_legacy_invoiced_settlement_is_identified_by_reconciliation(self):
        self._assert_legacy_settlement(invoice=True)

    def _assert_legacy_settlement(self, invoice=False):
        session = self._open_session()
        product = self.create_product("Legacy cash", self.categ_basic, 100)
        product.type = "service"
        order = self._order(session, product, 100)
        self.make_payment(order, self.cash_pm1, 100)
        if invoice:
            order.action_pos_order_invoice()
        session.try_cash_in_out("in", 20, "Float", False, {"translatedType": "in"})
        session.update_closing_cash_details(120)
        session.close_session_from_ui()
        session.statement_line_ids.pos_cash_move_type = False
        session.statement_line_ids.payment_ref = "Historical label"

        report = self.report.get_sale_details(session_ids=session.ids)

        row = next(row for row in report["payments"] if row["cash"])
        _logger.debug("Legacy reconciled cash row=%s", row)
        self.assertEqual(row["final_count"], 120)
        self.assertEqual([move["amount"] for move in row["cash_moves"]], [20])

    def test_legacy_difference_uses_session_and_accounts_after_rename(self):
        session = self._open_session()
        product = self.create_product("Legacy terminal", self.categ_basic, 100)
        order = self._order(session, product, 100)
        self.make_payment(order, self.bank_split_pm1, 100)
        session.action_pos_session_closing_control(
            bank_payment_method_diffs={self.bank_split_pm1.id: -20}
        )
        move = self.env["account.move"].search(
            [("pos_diff_session_id", "=", session.id)]
        )
        self.assertEqual(len(move), 1)
        move.pos_diff_payment_method_id = False
        move.ref = "Historical language and terminal name"
        self.bank_split_pm1.name = "Renamed terminal"

        report = self.report.get_sale_details(session_ids=session.ids)

        row = next(
            row for row in report["payments"] if row["id"] == self.bank_split_pm1.id
        )
        _logger.debug("Legacy linked difference after rename=%s", row)
        self.assertEqual(row["money_counted"], 80)
        self.assertEqual(row["money_difference"], -20)

    def test_ambiguous_legacy_difference_does_not_claim_zero(self):
        other = self.bank_split_pm1.copy({"name": "Second terminal"})
        self.config.payment_method_ids |= other
        session = self._open_session()
        product = self.create_product("Ambiguous terminals", self.categ_basic, 200)
        order = self._order(session, product, 200)
        self.make_payment(order, self.bank_split_pm1, 100)
        self.make_payment(order, other, 100)
        session.action_pos_session_closing_control(
            bank_payment_method_diffs={self.bank_split_pm1.id: -20}
        )
        move = self.env["account.move"].search(
            [("pos_diff_session_id", "=", session.id)]
        )
        move.pos_diff_payment_method_id = False
        move.ref = "Unknown historical reference"

        report = self.report.get_sale_details(session_ids=session.ids)

        rows = [row for row in report["payments"] if not row["cash"]]
        _logger.debug("Ambiguous legacy difference rows=%s", rows)
        self.assertEqual(sum(row["total"] for row in rows), 200)
        self.assertFalse(any(row["count"] for row in rows))

    def test_cashier_can_read_own_company_report_without_accounting_groups(self):
        session = self._open_session()
        product = self.create_product("Cashier report", self.categ_basic, 100)
        order = self._order(session, product, 100)
        self.make_payment(order, self.cash_pm1, 100)
        session.update_closing_cash_details(100)
        session.close_session_from_ui()
        session.statement_line_ids.pos_cash_move_type = False
        cashier = new_test_user(
            self.env,
            login="sale_details_cashier",
            groups="base.group_user,point_of_sale.group_pos_user",
        )

        report = self.report.with_user(cashier).get_sale_details(
            session_ids=session.ids
        )

        _logger.debug(
            "Cashier report paid=%s rows=%s", report["total_paid"], report["payments"]
        )
        self.assertEqual(report["total_paid"], 100)
        row = next(row for row in report["payments"] if row["cash"])
        self.assertEqual(row["money_difference"], 0)

    def test_cashier_cannot_report_another_company_session(self):
        other = self.setup_other_company(name="Private report company")["company"]
        other_config = (
            self.env["pos.config"]
            .with_company(other)
            .create({"name": "Private register"})
        )
        other_config.open_ui()
        cashier = new_test_user(
            self.env,
            login="restricted_report_cashier",
            groups="base.group_user,point_of_sale.group_pos_user",
            company_id=self.env.company.id,
        )

        for scope in (
            {"session_ids": other_config.current_session_id.ids},
            {"config_ids": other_config.ids},
        ):
            with self.subTest(scope=scope), self.assertRaises(AccessError):
                self.report.with_user(cashier).get_sale_details(**scope)

    def test_legacy_manual_expense_remains_when_drawer_balances(self):
        self.config.cash_control = True
        self.config.open_ui()
        session = self.config.current_session_id
        session.set_opening_control(100, None)
        session.try_cash_in_out(
            "out", 5, "Old expense", False, {"translatedType": "out"}
        )
        movement = session.statement_line_ids
        counterpart = movement.move_id.line_ids.filtered(
            lambda line: line.account_id == session.cash_journal_id.suspense_account_id
        )
        counterpart.account_id = session.cash_journal_id.loss_account_id
        movement.pos_cash_move_type = False
        session.update_closing_cash_details(95)
        session.close_session_from_ui()

        report = self.report.get_sale_details(session_ids=session.ids)

        row = next(row for row in report["payments"] if row["cash"])
        _logger.debug("Balanced legacy loss-account expense=%s", row)
        self.assertEqual([move["amount"] for move in row["cash_moves"]], [100, -5])
        self.assertEqual(row["money_difference"], 0)

    def test_multi_company_report_names_companies_without_unrelated_address(self):
        company = self.env.company
        company.partner_id.street = "First company street"
        other = self.setup_other_company(name="Second report company")["company"]
        other.partner_id.street = "Second company street"
        other_config = (
            self.env["pos.config"]
            .with_context(allowed_company_ids=[other.id, company.id])
            .create({"name": "Second register"})
        )
        configs = self.config | other_config
        data = {"config_ids": configs.ids, "employee_ids": []}

        rendered = (
            self.env["ir.actions.report"]
            .with_context(allowed_company_ids=[other.id, company.id])
            ._render_qweb_html(
                "point_of_sale.sale_details_report",
                [],
                data=data,
            )[0]
        )

        header = (
            lxml_html.fromstring(rendered).xpath('//*[@id="header"]')[0].text_content()
        )
        _logger.debug("Multi-company header=%s", header)
        self.assertIn(company.name, header)
        self.assertIn(other.name, header)
        self.assertNotIn(company.partner_id.street, header)
        self.assertNotIn(other.partner_id.street, header)

    def test_ambiguous_legacy_cash_detail_uses_recorded_transaction_total(self):
        self.config.cash_control = True
        self.config.open_ui()
        session = self.config.current_session_id
        session.set_opening_control(100, None)
        session.try_cash_in_out("out", 5, "Expense", False, {"translatedType": "out"})
        counterpart = session.statement_line_ids.move_id.line_ids.filtered(
            lambda line: line.account_id == session.cash_journal_id.suspense_account_id
        )
        counterpart.account_id = session.cash_journal_id.loss_account_id
        session.update_closing_cash_details(90)
        session.close_session_from_ui()
        self.assertEqual(session.cash_real_transaction, -5)
        self.assertEqual(len(session.statement_line_ids), 2)
        session.statement_line_ids.write(
            {"pos_cash_move_type": False, "payment_ref": "Old movement"}
        )

        report = self.report.get_sale_details(session_ids=session.ids)

        row = next(row for row in report["payments"] if row["cash"])
        _logger.debug(
            "Ambiguous legacy cash snapshot=%s row=%s",
            session.cash_real_transaction,
            row,
        )
        self.assertEqual(row["final_count"], 95)
        self.assertEqual(row["money_difference"], -5)
        self.assertEqual([move["amount"] for move in row["cash_moves"]], [100, -5])

    def test_secondary_cash_method_does_not_reuse_primary_drawer_count(self):
        journal = self.cash_pm1.journal_id.copy(
            {"name": "Secondary cash", "code": "CASH2"}
        )
        method = self.cash_pm1.copy(
            {
                "name": "Secondary cash",
                "journal_id": journal.id,
                "config_ids": [fields.Command.clear()],
            }
        )
        self.config.payment_method_ids |= method
        session = self._open_session()
        self.assertEqual(session.cash_journal_id, self.cash_pm1.journal_id)
        product = self.create_product("Two cash methods", self.categ_basic, 250)
        order = self._order(session, product, 250)
        self.make_payment(order, self.cash_pm1, 100)
        self.make_payment(order, method, 150)
        session.update_closing_cash_details(100)
        session.close_session_from_ui()

        report = self.report.get_sale_details(session_ids=session.ids)

        rows = {row["id"]: row for row in report["payments"]}
        _logger.debug("Primary and secondary cash counts=%s", rows)
        self.assertEqual(report["total_paid"], 250)
        self.assertEqual(rows[self.cash_pm1.id]["money_difference"], 0)
        self.assertFalse(rows[method.id]["count"])

    def test_archived_tax_remains_in_historical_report(self):
        tax = self.env["account.tax"].create({"name": "Historical VAT", "amount": 21})
        product = self.create_product(
            "Historical product", self.categ_basic, 100, tax_ids=tax.ids
        )
        session = self._open_session()
        order = self._order(session, product, 100, taxes=tax.ids)
        self.make_payment(order, self.bank_pm1, order.amount_total)
        self.assertEqual(order.state, "paid")
        before = self.report.get_sale_details(session_ids=session.ids)
        tax.active = False
        after = self.report.get_sale_details(session_ids=session.ids)
        _logger.debug(
            "Archived tax before=%s after=%s", before["taxes"], after["taxes"]
        )
        self.assertEqual(after["taxes"], before["taxes"])
        self.assertEqual(after["taxes_info"], {"base_amount": 100, "tax_amount": 21})

    def test_bank_profit_with_shared_profit_and_loss_account(self):
        journal = self.bank_split_pm1.journal_id
        journal.profit_account_id = journal.loss_account_id
        session = self._open_session()
        product = self.create_product(
            "Shared difference account", self.categ_basic, 100
        )
        order = self._order(session, product, 100)
        self.make_payment(order, self.bank_split_pm1, order.amount_total)
        session.action_pos_session_closing_control(
            bank_payment_method_diffs={self.bank_split_pm1.id: 10}
        )
        data = self.report.get_sale_details(session_ids=session.ids)
        row = next(
            row for row in data["payments"] if row["id"] == self.bank_split_pm1.id
        )
        _logger.debug("Shared profit/loss account row=%s", row)
        self.assertEqual(row["money_difference"], 10)
        self.assertEqual(row["money_counted"], 110)

    def test_bank_difference_survives_journal_account_changes(self):
        session = self._open_session()
        product = self.create_product(
            "Historical journal accounts", self.categ_basic, 100
        )
        order = self._order(session, product, 100)
        self.make_payment(order, self.bank_split_pm1, order.amount_total)
        session.action_pos_session_closing_control(
            bank_payment_method_diffs={self.bank_split_pm1.id: -10}
        )
        journal = self.bank_split_pm1.journal_id
        journal.write(
            {"loss_account_id": journal.loss_account_id.copy({"code": "LOSSNEW"}).id}
        )
        data = self.report.get_sale_details(session_ids=session.ids)
        row = next(
            row for row in data["payments"] if row["id"] == self.bank_split_pm1.id
        )
        _logger.debug("Changed journal accounts row=%s", row)
        self.assertEqual(row["money_difference"], -10)
        self.assertEqual(row["money_counted"], 90)

    def test_bank_counting_difference_without_sales_is_reported(self):
        session = self._open_session()
        session.action_pos_session_closing_control()
        method = self.bank_split_pm1
        moves = self.env["account.move"].create(
            {
                "journal_id": method.journal_id.id,
                "pos_diff_session_id": session.id,
                "pos_diff_payment_method_id": method.id,
                "line_ids": [
                    fields.Command.create(
                        {"account_id": method.outstanding_account_id.id, "debit": 10}
                    ),
                    fields.Command.create(
                        {
                            "account_id": method.journal_id.profit_account_id.id,
                            "credit": 10,
                        }
                    ),
                ],
            }
        )
        moves._post()
        data = self.report.get_sale_details(session_ids=session.ids)
        rows = [row for row in data["payments"] if row["id"] == self.bank_split_pm1.id]
        _logger.debug("No-sales bank difference moves=%s rows=%s", moves.ids, rows)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total"], 0)
        self.assertEqual(rows[0]["money_counted"], 10)

    def test_unposted_bank_difference_does_not_change_counted_amount(self):
        session = self._open_session()
        product = self.create_product("Unposted difference", self.categ_basic, 100)
        order = self._order(session, product, 100)
        self.make_payment(order, self.bank_split_pm1, order.amount_total)
        session.action_pos_session_closing_control(
            bank_payment_method_diffs={self.bank_split_pm1.id: -10}
        )
        move = self.env["account.move"].search(
            [("pos_diff_session_id", "=", session.id)]
        )
        move.action_draft()
        data = self.report.get_sale_details(session_ids=session.ids)
        row = next(
            row for row in data["payments"] if row["id"] == self.bank_split_pm1.id
        )
        _logger.debug("Unposted difference state=%s row=%s", move.state, row)
        self.assertEqual(row["money_difference"], 0)
