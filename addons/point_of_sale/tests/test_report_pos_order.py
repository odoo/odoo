from datetime import timedelta
from unittest.mock import patch

import odoo
from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user

from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.point_of_sale.tools import debug_log as dbg


@odoo.tests.tagged("post_install", "-at_install")
class TestReportPoSOrder(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def _create_report_order(self, quantities=(1,), price_unit=120, **values):
        product = self.create_product("Report product", self.categ_basic, price_unit)
        if not self.config.current_session_id:
            self.open_new_session()
        return self.env["pos.order"].create(
            {
                "session_id": self.config.current_session_id.id,
                "amount_total": price_unit * sum(quantities),
                "amount_tax": 0,
                "amount_paid": 0,
                "amount_return": 0,
                "lines": [
                    odoo.Command.create(
                        {
                            "product_id": product.id,
                            "qty": qty,
                            "price_unit": price_unit,
                            "price_subtotal": price_unit * qty,
                            "price_subtotal_incl": price_unit * qty,
                            "tax_ids": [odoo.Command.clear()],
                        }
                    )
                    for qty in quantities
                ],
                **values,
            }
        )

    def test_report_line_grain_and_first_dimensions(self):
        order = self._create_report_order((1, 2, -1, 0))
        categories = self.env["pos.category"].create(
            [
                {"name": "First report category"},
                {"name": "Second report category"},
            ]
        )
        order.lines.product_id.pos_categ_ids = categories
        methods = self.config.payment_method_ids.sorted("id")[:2]
        self.assertEqual(len(methods), 2)
        self.env["pos.payment"].create(
            [
                {
                    "pos_order_id": order.id,
                    "payment_method_id": method.id,
                    "amount": 120,
                }
                for method in reversed(methods)
            ]
        )
        self.env.flush_all()

        rows = self.env["report.pos.order"].search([("order_id", "=", order.id)])

        self.assertEqual(set(rows.ids), set(order.lines.ids))
        self.assertEqual(rows.payment_method_id, methods[-1])
        self.assertEqual(rows.pos_categ_id, categories[0])
        self.assertEqual(sum(rows.mapped("price_total")), 240)
        self.assertEqual(sum(rows.mapped("nbr_lines")), 4)
        self.assertEqual(rows[:1].action_view_order()["res_id"], order.id)
        with self.assertRaises(ValueError):
            rows.action_view_order()

    def test_report_currency_refunds_and_zero_rate(self):
        order = self._create_report_order((2, -1, 0))
        order.lines.product_id.pos_categ_ids = False
        order.lines.write({"discount": 25, "total_cost": 0})
        for line in order.lines:
            line.write(
                {
                    "price_subtotal": 90 * line.qty,
                    "price_subtotal_incl": 99 * line.qty,
                    "total_cost": 30 * line.qty,
                }
            )
        for rate, divisor in [(2, 2), (0, 1)]:
            with self.subTest(rate=rate):
                order.currency_rate = rate
                self.env.flush_all()
                report = self.env["report.pos.order"]
                report.invalidate_model()
                rows = report.search([("order_id", "=", order.id)])
                for row in rows:
                    qty = row.product_uom_qty
                    self.assertAlmostEqual(row.price_total, 99 * qty / divisor)
                    self.assertAlmostEqual(row.margin, 60 * qty / divisor)
                    self.assertAlmostEqual(row.discount_amount, 30 * qty / divisor)
                self.assertFalse(rows.payment_method_id)
                self.assertFalse(rows.pos_categ_id)
                self.assertEqual(rows.currency_id, order.company_id.currency_id)

    def test_report_zero_net_quantity_and_validation_delay(self):
        order = self._create_report_order((1, -1, 0))
        # Audit timestamps come from PostgreSQL. Anchor to the stored creation
        # date instead of trying to overwrite it or freeze Python's clock.
        order.date_order = order.create_date.replace(
            hour=0,
            minute=0,
            second=0,
        ) + timedelta(days=45)
        self.env.flush_all()

        report = self.env["report.pos.order"]
        rows = report.search([("order_id", "=", order.id)])
        [(average,)] = report._read_group(
            [("order_id", "=", order.id)],
            aggregates=["price_average:avg"],
        )

        self.assertFalse(average)
        self.assertEqual(rows.mapped("delay_validation"), [45, 45, 45])
        zero_line = rows.filtered(lambda row: not row.product_uom_qty)
        self.assertFalse(zero_line.price_average)

    def test_report_delay_defaults_to_average(self):
        first = self._create_report_order()
        second = self._create_report_order()
        first.date_order = first.create_date + timedelta(days=1)
        second.date_order = second.create_date + timedelta(days=2)
        self.env.flush_all()
        report = self.env["report.pos.order"]
        aggregator = report.fields_get(["delay_validation"])["delay_validation"][
            "aggregator"
        ]

        [(delay,)] = report._read_group(
            [("order_id", "in", (first | second).ids)],
            aggregates=[f"delay_validation:{aggregator}"],
        )

        self.assertAlmostEqual(delay, 1.5)
        # PivotRenderer chooses its formatter from this metadata. An integer
        # field hides the fractional part of an otherwise correct SQL average.
        self.assertEqual(
            report.fields_get(["delay_validation"])["delay_validation"]["type"], "float"
        )

    def test_report_pagination_orders_equal_dates_by_line_id(self):
        order = self._create_report_order((1, 2, 3))
        self.env.flush_all()
        report = self.env["report.pos.order"]
        domain = [("order_id", "=", order.id)]

        first_page = report.search(domain, limit=2)
        second_page = report.search(domain, offset=2, limit=2)

        self.assertEqual(
            first_page.ids + second_page.ids, sorted(order.lines.ids, reverse=True)
        )

    def test_report_uses_historical_currency_and_computed_cost(self):
        self.config = self.other_currency_config
        self.other_currency.rate_ids.unlink()
        self.env["res.currency.rate"].create(
            [
                {
                    "currency_id": self.other_currency.id,
                    "name": "2026-01-01",
                    "rate": 0.5,
                },
                {
                    "currency_id": self.other_currency.id,
                    "name": "2026-02-01",
                    "rate": 0.25,
                },
            ]
        )
        order = self._create_report_order((2, -1), date_order="2026-01-15 12:00:00")
        order.lines.product_id.standard_price = 20
        order.lines._update_total_cost(self.env["stock.move"])
        self.assertEqual(order.currency_id, self.other_currency)
        self.assertAlmostEqual(order.currency_rate, 0.5)

        rows = self.env["report.pos.order"].search([("order_id", "=", order.id)])

        lines_by_id = {line.id: line for line in order.lines}
        for row in rows:
            line = lines_by_id[row.id]
            self.assertAlmostEqual(line.total_cost, 10 * line.qty)
            self.assertAlmostEqual(row.price_subtotal, 240 * line.qty)
            self.assertAlmostEqual(row.margin, 220 * line.qty)
        self.assertEqual(rows.currency_id, self.company_currency)

    def test_report_flushes_pending_currency_recomputation(self):
        self.config = self.other_currency_config
        self.other_currency.rate_ids.unlink()
        self.env["res.currency.rate"].create(
            [
                {
                    "currency_id": self.other_currency.id,
                    "name": "2026-01-01",
                    "rate": 0.5,
                },
                {
                    "currency_id": self.other_currency.id,
                    "name": "2026-02-01",
                    "rate": 0.25,
                },
            ]
        )
        order = self._create_report_order(date_order="2026-01-15 12:00:00")
        cashier = new_test_user(
            self.env,
            login="report_flush_cashier",
            groups="point_of_sale.group_pos_user",
        )
        self.env.flush_all()
        order.date_order = "2026-02-15 12:00:00"

        [(total,)] = (
            self.env["report.pos.order"]
            .with_user(cashier)
            ._read_group(
                [("order_id", "=", order.id)],
                aggregates=["price_total:sum"],
            )
        )

        self.assertAlmostEqual(total, 480)

    def test_report_cached_values_refresh_after_source_change(self):
        order = self._create_report_order()
        report = self.env["report.pos.order"]
        domain = [("order_id", "=", order.id)]
        row = report.search(domain)
        self.assertAlmostEqual(row.price_total, 120)
        order.lines.write({"price_subtotal": 240, "price_subtotal_incl": 240})

        [(total,)] = report._read_group(domain, aggregates=["price_total:sum"])
        dbg.logic.debug(
            "Report cache before explicit invalidation: cached=%s aggregate=%s",
            row.price_total,
            total,
        )
        row.invalidate_recordset()

        self.assertAlmostEqual(total, 240)
        self.assertAlmostEqual(row.price_total, total)

    def test_report_filters_on_recomputed_configuration(self):
        order = self._create_report_order()
        self.config = self.other_currency_config
        self.open_new_session()
        self.env.flush_all()
        order.session_id = self.pos_session

        rows = self.env["report.pos.order"].search(
            [
                ("order_id", "=", order.id),
                ("config_id", "=", self.config.id),
            ]
        )

        self.assertEqual(rows.ids, order.lines.ids)
        self.assertEqual(rows.config_id, self.config)
        self.assertAlmostEqual(rows.price_total, 240)

    def test_report_clean_aggregate_needs_no_extra_flush_queries(self):
        order = self._create_report_order((1, 2, -1, 0))
        report = self.env["report.pos.order"]
        domain = [("order_id", "=", order.id)]
        report._read_group(domain, aggregates=["price_total:sum"])

        query_count = self.env.cr.sql_statement_count
        [(total,)] = report._read_group(domain, aggregates=["price_total:sum"])
        query_count = self.env.cr.sql_statement_count - query_count

        dbg.performance.debug("Clean POS aggregate: %d SQL statements", query_count)
        self.assertAlmostEqual(total, 240)
        self.assertLessEqual(query_count, 1)

    def test_average_price_uses_reported_product_unit(self):
        order = self._create_report_order((1, 3))
        dozen = self.env["uom.uom"].create(
            {
                "name": "Report dozen",
                "relative_factor": 12,
                "relative_uom_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        order.lines.product_id.uom_id = dozen
        order.lines[1].write(
            {"price_unit": 240, "price_subtotal": 720, "price_subtotal_incl": 720}
        )
        self.env.flush_all()

        [(average,)] = self.env["report.pos.order"]._read_group(
            [("order_id", "=", order.id)],
            aggregates=["price_average:avg"],
        )

        self.assertAlmostEqual(average, 210)
        rows = self.env["report.pos.order"].search([("order_id", "=", order.id)])
        self.assertEqual(rows.product_uom_id, dozen)

    def test_report_keeps_config_without_session(self):
        order = self._create_report_order()
        order.session_id = False
        self.assertEqual(order.config_id, self.config)
        self.env.flush_all()

        row = self.env["report.pos.order"].search([("order_id", "=", order.id)])

        self.assertEqual(row.config_id, self.config)
        self.assertFalse(row.session_id)

    def test_invoice_report_deduplicates_and_forwards_render_data(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
            }
        )
        invoice.company_id.account_config_id.qr_code = True
        orders = self._create_report_order(account_move=invoice.id)
        orders |= self._create_report_order(account_move=invoice.id)
        report = self.env["report.point_of_sale.report_invoice"]

        for report_type in ("html", "pdf", None):
            with (
                self.subTest(report_type=report_type),
                patch.object(
                    type(invoice),
                    "_generate_qr_code",
                    return_value="report-qr",
                ) as generate,
            ):
                values = report._get_report_values(
                    orders.ids,
                    data={"report_type": report_type} if report_type else None,
                )

                self.assertEqual(values["docs"].ids, invoice.ids)
                self.assertEqual(values["doc_ids"], invoice.ids)
                self.assertEqual(values["doc_model"], "account.move")
                self.assertEqual(values["qr_code_urls"], {invoice.id: "report-qr"})
                generate.assert_called_once_with(silent_errors=report_type == "html")

    def test_invoice_report_rejects_uninvoiced_and_unauthorized_orders(self):
        order = self._create_report_order()
        report = self.env["report.point_of_sale.report_invoice"]
        with self.assertRaisesRegex(UserError, "No link to an invoice"):
            report._get_report_values(order.ids)
        user = new_test_user(
            self.env, login="report_no_pos_access", groups="base.group_user"
        )
        with self.assertRaises(AccessError):
            report.with_user(user)._get_report_values(order.ids)

    def test_invoice_report_allows_cashier_and_empty_selection(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
            }
        )
        invoice.company_id.account_config_id.qr_code = False
        order = self._create_report_order(account_move=invoice.id)
        user = new_test_user(
            self.env, login="report_cashier", groups="point_of_sale.group_pos_user"
        )
        report = self.env["report.point_of_sale.report_invoice"].with_user(user)

        values = report._get_report_values(order.ids)

        self.assertEqual(values["docs"].ids, invoice.ids)
        self.assertEqual(values["docs"].env.uid, user.id)
        self.assertFalse(values["docs"].env.su)
        self.assertFalse(report._get_report_values([])["docs"])

    def test_invoice_report_respects_invoice_record_rules(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
            }
        )
        invoice.company_id.account_config_id.qr_code = False
        order = self._create_report_order(account_move=invoice.id)
        user = new_test_user(
            self.env,
            login="report_restricted_cashier",
            groups="point_of_sale.group_pos_user",
        )
        order.with_user(user).check_access("read")
        invoice.with_user(user).check_access("read")
        self.env["ir.rule"].create(
            {
                "name": "Deny this invoice even when its POS order is readable",
                "model_id": self.env["ir.model"]._get_id("account.move"),
                "domain_force": repr([("id", "!=", invoice.id)]),
            }
        )

        with self.assertRaises(AccessError):
            invoice.with_user(user).check_access("read")
        with self.assertRaises(AccessError):
            self.env["report.point_of_sale.report_invoice"].with_user(
                user
            )._get_report_values(order.ids)

    def test_invoice_report_renders_consolidated_invoice_as_cashier(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    odoo.Command.create(
                        {
                            "name": "Unique consolidated report line",
                            "quantity": 1,
                            "price_unit": 120,
                        }
                    )
                ],
            }
        )
        invoice.company_id.account_config_id.qr_code = True
        orders = self._create_report_order(account_move=invoice.id)
        orders |= self._create_report_order(account_move=invoice.id)
        user = new_test_user(
            self.env,
            login="report_render_cashier",
            groups="point_of_sale.group_pos_user",
        )
        # This legacy adapter has no shipped action/template. Supply one only
        # for this test so the real report service and QWeb exercise its values.
        self.env["ir.ui.view"].create(
            {
                "name": "POS invoice adapter test",
                "type": "qweb",
                "key": "point_of_sale.report_invoice",
                "arch": '<t t-name="point_of_sale.report_invoice"><t t-call="account.report_invoice"/></t>',
            }
        )
        action = self.env["ir.actions.report"].create(
            {
                "name": "POS invoice adapter test",
                "model": "pos.order",
                "report_type": "qweb-html",
                "report_name": "point_of_sale.report_invoice",
            }
        )

        for qr_enabled in (False, True):
            with self.subTest(qr_enabled=qr_enabled):
                invoice.company_id.account_config_id.qr_code = qr_enabled
                html, _ = (
                    self.env["ir.actions.report"]
                    .with_user(user)
                    ._render_qweb_html(
                        action,
                        orders.ids,
                    )
                )

                self.assertEqual(html.count(b"Unique consolidated report line"), 1)

    def test_reports_respect_company_rules(self):
        order = self._create_report_order()
        company = self.env["res.company"].create({"name": "Other report company"})
        user = new_test_user(
            self.env,
            login="report_other_company",
            groups="point_of_sale.group_pos_manager",
            company_id=company.id,
            company_ids=[odoo.Command.set(company.ids)],
        )
        self.env.flush_all()

        rows = (
            self.env["report.pos.order"]
            .with_user(user)
            .search(
                [
                    ("order_id", "=", order.id),
                ]
            )
        )

        self.assertFalse(rows)
        with self.assertRaises(AccessError):
            self.env["report.point_of_sale.report_invoice"].with_user(
                user
            )._get_report_values(order.ids)

    def test_report_totals_with_tax_and_discount(self):
        for discount, taxed, subtotal, total, discount_amount in [
            (0, False, 150, 150, 0),
            (0, True, 150, 165, 0),
            (10, False, 135, 135, 15),
            (10, True, 135, 148.5, 15),
        ]:
            with self.subTest(discount=discount, taxed=taxed):
                order = self._create_report_order(price_unit=150)
                order.lines.write(
                    {
                        "discount": discount,
                        "tax_ids": [
                            odoo.Command.set(self.taxes["tax10"].ids if taxed else [])
                        ],
                        "price_subtotal": subtotal,
                        "price_subtotal_incl": total,
                    }
                )
                order.write({"amount_total": total, "amount_tax": total - subtotal})
                self.env.flush_all()

                rows = self.env["report.pos.order"].search(
                    [("order_id", "=", order.id)]
                )

                self.assertRecordValues(
                    rows,
                    [
                        {
                            "nbr_lines": 1,
                            "product_uom_qty": 1,
                            "price_subtotal": subtotal,
                            "price_total": total,
                            "price_average": 150,
                            "price_subtotal_nodiscount": 150,
                            "discount_amount": discount_amount,
                            "margin": subtotal,
                        }
                    ],
                )
