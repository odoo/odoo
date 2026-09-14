from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.sale_project.tests.common import TestSaleProjectCommon


@tagged("post_install", "-at_install")
class TestSaleProjectServices(TestSaleProjectCommon):
    def test_get_first_service_line_returns_service(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_consumable.id,
                            "product_qty": 1,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_service_ordered_prepaid.id,
                            "product_qty": 1,
                        }
                    ),
                ],
            }
        )
        line = order.get_first_service_line()
        self.assertEqual(line.product_id, self.product_service_ordered_prepaid)

    def test_get_first_service_line_requires_service(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_consumable.id,
                            "product_qty": 1,
                        }
                    )
                ],
            }
        )
        with self.assertRaises(UserError):
            order.get_first_service_line()

    def test_a_non_billable_project_keeps_and_propagates_its_customer(self):
        partner = self.env["res.partner"].create({"name": "Non-billable customer"})
        project = self.env["project.project"].create(
            {"name": "Not billed", "allow_billable": False, "partner_id": partner.id}
        )
        partner.company_id = self.env.company
        self.assertEqual(project.partner_id, partner)
        self.assertFalse(project._is_partner_hidden())

        task = self.env["project.task"].create(
            {"name": "Task", "project_id": project.id}
        )
        child = self.env["project.task"].create(
            {"name": "Child", "project_id": project.id, "parent_id": task.id}
        )
        self.assertEqual(task.partner_id, partner)
        self.assertEqual(child.partner_id, partner)

    def test_moving_a_customer_to_another_company_is_refused(self):
        other_company = self.env["res.company"].create({"name": "Other company"})
        partner = self.env["res.partner"].create({"name": "Moving customer"})
        project = self.env["project.project"].create(
            {
                "name": "Company project",
                "allow_billable": False,
                "partner_id": partner.id,
                "company_id": self.env.company.id,
            }
        )
        with self.assertRaises(UserError):
            partner.company_id = other_company
        self.assertEqual(project.partner_id, partner)

    def test_has_any_so_to_invoice_uses_fork_state_spelling(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_service_ordered_prepaid.id,
                            "product_qty": 5,
                            "tax_ids": False,
                        }
                    ),
                ],
            }
        )
        order.action_confirm()
        self.project_global.sale_line_id = order.line_ids[0]
        self.env.invalidate_all()

        self.assertEqual(order.invoice_state, "to do")
        self.assertTrue(self.project_global.has_any_so_to_invoice)

        invoice = order._create_invoices()
        invoice.action_post()
        self.env.invalidate_all()

        self.assertEqual(order.invoice_state, "done")
        self.assertFalse(self.project_global.has_any_so_to_invoice)

    def test_project_update_description_renders_for_a_billable_project(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_service_ordered_prepaid.id,
                            "product_qty": 5,
                            "tax_ids": False,
                        }
                    ),
                ],
            }
        )
        order.action_confirm()
        project = order.project_ids[:1] or self.project_global
        project.allow_billable = True
        project.sale_line_id = order.line_ids[0]

        description = self.env["project.update"]._prepare_description(project)
        self.assertTrue(description)

        update = self.env["project.update"].create(
            {"name": "Update", "project_id": project.id, "status": "on_track"}
        )
        self.assertTrue(update.exists())
