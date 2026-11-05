from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTimesheetBilling(TransactionCase):
    """Tests for the Timesheet → Invoice flow (G-12 / WS-13).

    Acceptance criteria:

    * a timesheet linked to a "delivered by timesheet" sales order line is
      flagged billable and unbilled;
    * the project and the sales order expose the unbilled count/hours;
    * invoicing from timesheets creates an invoice, links the timesheets to it
      and clears the unbilled flag;
    * the wizard refuses draft orders and invoices a selected date range.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_hour = cls.env.ref("uom.product_uom_hour")

        cls.income_account = cls.env["account.account"].create(
            {
                "name": "Service Income TSB",
                "code": "400999",
                "account_type": "income",
            }
        )
        cls.receivable_account = cls.env["account.account"].create(
            {
                "name": "Receivable TSB",
                "code": "121999",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        cls.sale_journal = cls.env["account.journal"].create(
            {
                "name": "Sales TSB",
                "code": "TSBJ",
                "type": "sale",
            }
        )
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Customer TSB",
                "is_company": True,
                "property_account_receivable_id": cls.receivable_account.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Service Timesheet TSB",
                "type": "service",
                "invoice_policy": "delivery",
                "service_type": "timesheet",
                "service_tracking": "no",
                "uom_id": cls.uom_hour.id,
                "list_price": 100.0,
                "taxes_id": False,
                "property_account_income_id": cls.income_account.id,
            }
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "Timesheet Billing Project",
                "allow_timesheets": True,
                "allow_billable": True,
                "partner_id": cls.customer.id,
            }
        )
        cls.employee = cls.env["hr.employee"].create({"name": "Employee TSB"})

    def _make_order(self, qty=10.0):
        order = self.env["sale.order"].create({"partner_id": self.customer.id})
        self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_uom_qty": qty,
            }
        )
        return order

    def _log_time(self, order, hours=3.0):
        so_line = order.order_line[:1]
        return self.env["account.analytic.line"].create(
            {
                "name": "Work TSB",
                "project_id": self.project.id,
                "so_line": so_line.id,
                "is_so_line_edited": True,
                "unit_amount": hours,
                "employee_id": self.employee.id,
            }
        )

    def test_unbilled_flag_and_counters(self):
        order = self._make_order()
        order.action_confirm()
        timesheet = self._log_time(order, hours=4.0)

        self.assertTrue(
            timesheet.od19_is_billable_unbilled,
            "Timesheet ของงานที่เรียกเก็บตามเวลาต้องถูกทำเครื่องหมายว่ารอเรียกเก็บ",
        )
        self.assertEqual(order.od19_unbilled_timesheet_count, 1)
        self.assertAlmostEqual(order.od19_unbilled_timesheet_hours, 4.0)
        self.assertEqual(self.project.od19_unbilled_timesheet_count, 1)
        self.assertAlmostEqual(self.project.od19_unbilled_timesheet_hours, 4.0)

    def test_search_unbilled_timesheets(self):
        order = self._make_order()
        order.action_confirm()
        timesheet = self._log_time(order)
        found = self.env["account.analytic.line"].search(
            [("od19_is_billable_unbilled", "=", True)]
        )
        self.assertIn(timesheet, found)
        not_found = self.env["account.analytic.line"].search(
            [("od19_is_billable_unbilled", "!=", True)]
        )
        self.assertNotIn(timesheet, not_found)

    def test_invoice_from_timesheets_links_and_clears_flag(self):
        order = self._make_order()
        order.action_confirm()
        timesheet = self._log_time(order, hours=5.0)

        action = order.action_od19_create_invoice_from_timesheets()
        invoices = self.env["account.move"].browse(action["domain"][0][2])
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices.move_type, "out_invoice")
        self.assertEqual(timesheet.timesheet_invoice_id, invoices)
        self.assertFalse(timesheet.od19_is_billable_unbilled)
        self.assertEqual(order.od19_unbilled_timesheet_count, 0)

    def test_invoice_action_requires_confirmed_order(self):
        order = self._make_order()
        self._log_time(order)
        with self.assertRaises(UserError):
            order.action_od19_create_invoice_from_timesheets()

    def test_wizard_requires_confirmed_order(self):
        order = self._make_order()
        wizard = self.env["od19.timesheet.invoice.wizard"].create(
            {"sale_order_ids": [(6, 0, order.ids)]}
        )
        with self.assertRaises(UserError):
            wizard.action_create_invoices()

    def test_wizard_creates_invoice(self):
        order = self._make_order()
        order.action_confirm()
        timesheet = self._log_time(order, hours=2.0)

        wizard = self.env["od19.timesheet.invoice.wizard"].create(
            {"sale_order_ids": [(6, 0, order.ids)]}
        )
        action = wizard.action_create_invoices()
        invoices = self.env["account.move"].browse(action["domain"][0][2])
        self.assertEqual(len(invoices), 1)
        self.assertEqual(timesheet.timesheet_invoice_id, invoices)
