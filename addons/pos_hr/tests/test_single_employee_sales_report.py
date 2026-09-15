import logging
from datetime import timedelta

import odoo
from odoo import fields

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

_logger = logging.getLogger(__name__)


@odoo.tests.tagged("post_install", "-at_install")
class TestSingleEmployeeSalesReport(TestPoSCommon):
    """The per-employee block is printed beside the session block on one page,
    so it must answer the same question over the same period."""

    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.report = self.env["report.point_of_sale.report_saledetails"]
        self.employee_report = self.env["report.pos_hr.single_employee_sales_report"]

    def test_employee_block_covers_the_window_it_was_asked_for(self):
        product = self.create_product("Sold Last Week", self.categ_basic, 100)
        self.config.open_ui()
        session = self.config.current_session_id
        session.set_opening_control(0, None)
        order = self.env["pos.order"].create(
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
                            "price_unit": 100,
                            "discount": 0,
                            "qty": 1,
                            "tax_ids": [],
                            "price_subtotal": 100,
                            "price_subtotal_incl": 100,
                        },
                    )
                ],
                "pricelist_id": self.config.pricelist_id.id,
                "amount_paid": 100.0,
                "amount_total": 100.0,
                "amount_tax": 0.0,
                "amount_return": 0.0,
                "last_order_preparation_change": "{}",
                "to_invoice": False,
            }
        )
        self.make_payment(order, self.bank_pm1, 100)
        order.sudo().date_order = fields.Datetime.now() - timedelta(days=10)

        window = (
            fields.Datetime.to_string(fields.Datetime.now() - timedelta(days=11)),
            fields.Datetime.to_string(fields.Datetime.now() - timedelta(days=9)),
        )
        session_report = self.report.get_sale_details(*window, self.config.ids)
        employee_report = self.employee_report.get_sale_details(
            *window, self.config.ids
        )
        self.assertEqual(session_report["nbr_orders"], 1)
        self.assertEqual(
            employee_report["nbr_orders"],
            session_report["nbr_orders"],
            "the employee block silently dropped the requested date range",
        )

    def test_wizard_renders_the_employee_blocks(self):
        """The per-employee blocks are rendered by a template that calls
        ``get_sale_details`` itself, so nothing but a render exercises them."""
        product = self.create_product("Rendered", self.categ_basic, 100)
        self.config.open_ui()
        session = self.config.current_session_id
        session.set_opening_control(0, None)
        order = self.env["pos.order"].create(
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
                            "price_unit": 100,
                            "discount": 0,
                            "qty": 1,
                            "tax_ids": [],
                            "price_subtotal": 100,
                            "price_subtotal_incl": 100,
                        },
                    )
                ],
                "pricelist_id": self.config.pricelist_id.id,
                "amount_paid": 100.0,
                "amount_total": 100.0,
                "amount_tax": 0.0,
                "amount_return": 0.0,
                "last_order_preparation_change": "{}",
                "to_invoice": False,
            }
        )
        self.make_payment(order, self.bank_pm1, 100)
        employee = self.env["hr.employee"].sudo().create({"name": "Report Cashier"})
        order.sudo().employee_id = employee.id
        analysis = self.env["report.pos.order"].search([("order_id", "=", order.id)])
        self.assertEqual(analysis.employee_id, employee)
        self.assertEqual(analysis.order_id, order)
        self.assertAlmostEqual(sum(analysis.mapped("price_total")), 100)

        wizard = self.env["pos.daily.sales.reports.wizard"].create(
            {"pos_session_id": session.id}
        )
        data = wizard._prepare_report_params()
        self.assertIn(employee.id, data["employee_ids"])

        html = self.env["ir.actions.report"]._render_qweb_html(
            "point_of_sale.sale_details_report", [], data=data
        )[0]
        self.assertIn(b"Employee Sales Report", html)
        self.assertIn(employee.name.encode(), html)

    def test_employee_invoices_exclude_other_cashiers(self):
        product = self.create_product("Cashier invoice", self.categ_basic, 100)
        product.type = "service"
        self._start_pos_session(self.bank_pm1, 0)
        orders = self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(product, 1)],
                    "payments": [(self.bank_pm1, 100)],
                    "uuid": f"employee-report-{index}",
                }
                for index in range(2)
            ]
        )
        employees = (
            self.env["hr.employee"]
            .sudo()
            .create(
                [
                    {"name": "First report cashier"},
                    {"name": "Second report cashier"},
                ]
            )
        )
        for order, employee in zip(orders.values(), employees, strict=True):
            order.employee_id = employee
            order.partner_id = self.partner_a
            order.action_pos_order_invoice()
        selected = orders["employee-report-0"]

        report = self.employee_report.get_sale_details(
            session_ids=selected.session_id.ids,
            employee_id=employees[0].id,
        )

        invoices = [
            row for group in report["invoice_list"] for row in group["invoices"]
        ]
        _logger.debug(
            "Employee report invoices=%s payments=%s", invoices, report["payments"]
        )
        self.assertEqual(report["nbr_orders"], 1)
        self.assertEqual(
            [row["name"] for row in invoices], [selected.account_move.name]
        )
        self.assertEqual(report["invoice_total"], 100)
        self.assertFalse(any(row["count"] for row in report["payments"]))
