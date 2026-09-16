from odoo import Command
from odoo.tests import tagged

from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet


@tagged("-at_install", "post_install")
class TestSaleTimesheetMargin(TestCommonSaleTimesheet):
    def setUp(self):
        super().setUp()
        uom_day_id = self.ref("uom.product_uom_day")
        self.uom_day = self.env["uom.uom"].browse(uom_day_id)
        self.product_1 = self.env["product.product"].create(
            {
                "name": "Service Ordered, create no task, uom day",
                "list_price": 1.0,
                "type": "service",
                "invoice_policy": "ordered",
                "uom_id": uom_day_id,
                "default_code": "SERV-ORDERED-DAY",
                "service_type": "timesheet",
                "service_tracking": "task_in_project",
                "project_id": False,
                "taxes_id": False,
            }
        )
        self.employee_manager.hourly_cost = 10

    def test_sale_timesheet_margin(self):
        sale_order = self.env["sale.order"].create(
            {
                "name": "Test_SO0001",
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_1.id,
                            "price_unit": 1.0,
                            "product_uom_id": self.uom_day.id,
                            "product_qty": 1.0,
                        }
                    )
                ],
                "partner_id": self.partner_b.id,
                "partner_invoice_id": self.partner_b.id,
                "partner_shipping_id": self.partner_b.id,
            }
        )
        sale_order.action_confirm()

        self.env["account.analytic.line"].create(
            {
                "name": "Test Line",
                "unit_amount": 2,
                "employee_id": self.employee_manager.id,
                "project_id": sale_order.project_ids.id,
                "task_id": sale_order.line_ids.task_id.id,
                "account_id": self.analytic_account_sale.id,
                "so_line": sale_order.line_ids.id,
            }
        )
        sale_order.line_ids._compute_purchase_price()
        expected_cost = self.uom_day._get_quantity_in_unit(
            self.employee_manager.hourly_cost, self.env.company.project_time_mode_id
        )
        self.assertEqual(
            sale_order.line_ids.purchase_price,
            expected_cost,
            "Sale order line cost should be number of working hours on one day * timesheet cost of the employee set on the timesheet linked to the SOL.",
        )

    def test_no_recompute_purchase_price_not_timesheet(self):
        project = self.env["project.project"].create(
            {
                "name": "Test",
            }
        )
        self.product_1.write(
            {
                "uom_id": self.ref("uom.product_uom_unit"),
                "service_type": "timesheet",
                "service_policy": "ordered_prepaid",
                "service_tracking": "task_global_project",
                "project_id": project.id,
                "standard_price": 2,
            }
        )
        simple_service = self.env["product.product"].create(
            {
                "name": "Simple service",
                "list_price": 1.0,
                "type": "service",
                "invoice_policy": "ordered",
                "service_type": "timesheet",
                "standard_price": 5,
            }
        )
        sale_order = self.env["sale.order"].create(
            {
                "name": "Test_SO0002",
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_1.id,
                            "price_unit": 1.0,
                            "product_qty": 1.0,
                        }
                    )
                ],
                "partner_id": self.partner_b.id,
                "partner_invoice_id": self.partner_b.id,
                "partner_shipping_id": self.partner_b.id,
            }
        )
        sale_order.line_ids.purchase_price = 3
        sale_order.action_confirm()
        self.env["account.analytic.line"].create(
            {
                "name": "Test Line 222",
                "unit_amount": 2,
                "amount": 1,
                "employee_id": self.employee_manager.id,
                "project_id": project.id,
                "task_id": sale_order.line_ids.task_id.id,
                "account_id": self.analytic_account_sale.id,
                "so_line": sale_order.line_ids.id,
            }
        )
        self.env.flush_all()
        self.assertEqual(
            sale_order.line_ids.filtered(
                lambda sol: sol.product_id == self.product_1
            ).purchase_price,
            3,
        )
        sale_order.line_ids = [
            Command.create(
                {
                    "product_id": simple_service.id,
                    "price_unit": 1.0,
                    "product_qty": 1.0,
                }
            )
        ]
        self.assertEqual(
            sale_order.line_ids.filtered(
                lambda sol: sol.product_id == simple_service
            ).purchase_price,
            5,
        )
