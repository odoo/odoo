from datetime import datetime

from odoo import Command
from odoo.libs.numbers import float_compare
from odoo.tests import tagged

from odoo.addons.project.tests.test_project_profitability import (
    TestProjectProfitabilityCommon as Common,
)
from odoo.addons.sale.tests.common import TestSaleCommon


class TestProjectProfitabilityCommon(Common):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("sale.group_sale_manager")
        uom_unit_id = cls.env.ref("uom.product_uom_unit").id

        cls.material_product = cls.env["product.product"].create(
            {
                "name": "Material",
                "type": "consu",
                "standard_price": 5,
                "list_price": 10,
                "invoice_policy": "ordered",
                "uom_id": uom_unit_id,
            }
        )

        cls.uom_hour = cls.env.ref("uom.product_uom_hour")
        cls.product_delivery_service = cls.env["product.product"].create(
            {
                "name": "Service Delivery, create task in global project",
                "standard_price": 30,
                "list_price": 90,
                "type": "service",
                "invoice_policy": "transferred",
                "service_type": "manual",
                "uom_id": cls.uom_hour.id,
                "default_code": "SERV-ORDERED2",
                "service_tracking": "task_global_project",
                "project_id": cls.project.id,
            }
        )
        cls.down_payment_product = cls.env["product.product"].create(
            {
                "name": "downpayment product, used to simulate down payments",
                "standard_price": 30,
                "type": "service",
                "service_policy": "ordered_prepaid",
            }
        )
        cls.sale_order = (
            cls.env["sale.order"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "partner_id": cls.partner.id,
                    "partner_invoice_id": cls.partner.id,
                    "partner_shipping_id": cls.partner.id,
                }
            )
        )
        SaleOrderLine = cls.env["sale.order.line"].with_context(
            tracking_disable=True, default_order_id=cls.sale_order.id
        )
        cls.delivery_service_order_line = SaleOrderLine.create(
            {
                "product_id": cls.product_delivery_service.id,
                "product_qty": 10,
            }
        )
        cls.sale_order.action_confirm()

        cls.analytic_account_nb = cls.env["account.analytic.account"].create(
            {
                "name": "Project non billable AA",
                "code": "AA-123456",
                "plan_id": cls.analytic_plan.id,
            }
        )

        cls.project_non_billable = (
            cls.env["project.project"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Non Billable Project",
                    "account_id": cls.analytic_account_nb.id,
                    "allow_billable": False,
                    "partner_id": False,
                }
            )
        )
        cls.project_billable_no_company = cls.env["project.project"].create(
            {"name": "project billable", "allow_billable": True}
        )
        cls.project_billable_no_company._create_analytic_account()


@tagged("-at_install", "post_install")
class TestSaleProjectProfitability(TestProjectProfitabilityCommon, TestSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

    def test_profitability_of_non_billable_project(self):
        self.env["account.analytic.line"].create(
            [
                {
                    "name": "other revenues line",
                    "account_id": self.project_non_billable.account_id.id,
                    "amount": 100,
                },
                {
                    "name": "other costs line",
                    "account_id": self.project_non_billable.account_id.id,
                    "amount": -100,
                },
            ]
        )
        self.assertFalse(self.project_non_billable.allow_billable)
        panel_data = self.project_non_billable.get_panel_data()
        self.assertFalse(panel_data.get("profitability_items"))
        self.assertFalse(panel_data.get("profitability_labels"))
        self.project_non_billable.write(
            {"sale_line_id": self.sale_order.line_ids[0].id}
        )
        panel_data = self.project_non_billable.get_panel_data()
        self.assertFalse(
            panel_data.get("profitability_items"),
            "Even if the project has a sale order item linked, the project profitability should not be computed since it is not billable.",
        )
        self.assertFalse(
            panel_data.get("profitability_labels"),
            "Even if the project has a sale order item linked, the project profitability should not be computed since it is not billable.",
        )

    def test_project_profitability(self):
        foreign_company = self.company_data_2["company"]
        foreign_company.currency_id = self.foreign_currency
        companies = foreign_company | self.sale_order.company_id
        self.project.company_id = False
        self.assertFalse(
            self.project.allow_billable, "The project should be non billable."
        )
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            "No data for the project profitability should be found since the project is not billable, so no SOL is linked to the project.",
        )
        self.project.write({"allow_billable": True})
        self.assertTrue(self.project.allow_billable, "The project should be billable.")
        self.project.sale_line_id = self.delivery_service_order_line
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            "No data for the project profitability should be found since no product is delivered in the SO linked.",
        )

        self.env["account.analytic.line"].create(
            [
                {
                    "name": "other revenues line",
                    "account_id": self.project.account_id.id,
                    "amount": 100,
                },
                {
                    "name": "other costs line",
                    "account_id": self.project.account_id.id,
                    "amount": -100,
                },
            ]
        )

        product_delivery_service_foreign = (
            self.env["product.product"]
            .with_company(foreign_company)
            .create(
                {
                    "name": "Service Delivery, create task in global project",
                    "standard_price": 30,
                    "list_price": 90,
                    "type": "service",
                    "invoice_policy": "transferred",
                    "service_type": "manual",
                    "uom_id": self.uom_hour.id,
                    "default_code": "SERV-ORDERED2",
                    "service_tracking": "task_global_project",
                    "project_id": self.project.id,
                }
            )
        )
        sale_order_foreign = (
            self.env["sale.order"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "partner_id": self.partner.id,
                    "partner_invoice_id": self.partner.id,
                    "partner_shipping_id": self.partner.id,
                    "company_id": foreign_company.id,
                }
            )
        )
        sale_order_foreign.currency_id = self.foreign_currency.id
        sol_foreign = (
            self.env["sale.order.line"]
            .with_context(tracking_disable=True, default_order_id=sale_order_foreign.id)
            .create(
                {
                    "product_id": product_delivery_service_foreign.id,
                    "product_qty": 10,
                    "company_id": foreign_company.id,
                }
            )
        )
        sale_order_foreign.action_confirm()
        sol_foreign.qty_transferred = 1
        service_policy_to_invoice_type = (
            self.project._get_service_policy_to_invoice_type()
        )
        invoice_type = service_policy_to_invoice_type[
            self.delivery_service_order_line.product_id.service_policy
        ]
        self.assertIn(
            invoice_type,
            ["billable_manual", "service_revenues"],
            'invoice_type="billable_manual" if sale_timesheet is installed otherwise it is equal to "service_revenues"',
        )
        sequence_per_invoice_type = (
            self.project._get_profitability_sequence_per_invoice_type()
        )
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                "revenues": {
                    "data": [
                        {
                            "id": "other_revenues_aal",
                            "sequence": sequence_per_invoice_type["other_revenues_aal"],
                            "invoiced": 100.0,
                            "to_invoice": 0.0,
                        },
                        {
                            "id": invoice_type,
                            "sequence": sequence_per_invoice_type[invoice_type],
                            "to_invoice": sol_foreign.amount_taxexc_to_invoice * 0.2,
                            "invoiced": 0.0,
                        },
                    ],
                    "total": {
                        "to_invoice": sol_foreign.amount_taxexc_to_invoice * 0.2,
                        "invoiced": 100.0,
                    },
                },
                "costs": {
                    "data": [
                        {
                            "id": "other_costs_aal",
                            "sequence": sequence_per_invoice_type["other_costs_aal"],
                            "billed": -100.0,
                            "to_bill": 0.0,
                        }
                    ],
                    "total": {"billed": -100.0, "to_bill": 0.0},
                },
            },
        )
        self.assertNotEqual(sol_foreign.amount_taxexc_to_invoice, 0.0)
        self.assertEqual(sol_foreign.amount_taxexc_invoiced, 0.0)

        self.delivery_service_order_line.qty_transferred = 1
        self.assertIn("service_revenues", sequence_per_invoice_type)
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                "revenues": {
                    "data": [
                        {
                            "id": "other_revenues_aal",
                            "sequence": sequence_per_invoice_type["other_revenues_aal"],
                            "invoiced": 100.0,
                            "to_invoice": 0.0,
                        },
                        {
                            "id": invoice_type,
                            "sequence": sequence_per_invoice_type[invoice_type],
                            "to_invoice": self.delivery_service_order_line.amount_taxexc_to_invoice
                            + sol_foreign.amount_taxexc_to_invoice * 0.2,
                            "invoiced": 0.0,
                        },
                    ],
                    "total": {
                        "to_invoice": self.delivery_service_order_line.amount_taxexc_to_invoice
                        + sol_foreign.amount_taxexc_to_invoice * 0.2,
                        "invoiced": 100,
                    },
                },
                "costs": {
                    "data": [
                        {
                            "id": "other_costs_aal",
                            "sequence": sequence_per_invoice_type["other_costs_aal"],
                            "billed": -100.0,
                            "to_bill": 0.0,
                        }
                    ],
                    "total": {"billed": -100.0, "to_bill": 0.0},
                },
            },
        )
        self.assertNotEqual(
            self.delivery_service_order_line.amount_taxexc_to_invoice, 0.0
        )
        self.assertEqual(self.delivery_service_order_line.amount_taxexc_invoiced, 0.0)

        context = {
            "active_model": "sale.order",
            "active_ids": sale_order_foreign.ids,
            "active_id": sale_order_foreign.id,
            "allowed_company_ids": companies.ids,
        }
        invoices_foreign = (
            self.env["sale.advance.payment.inv"]
            .with_context(context)
            .create(
                {
                    "advance_payment_method": "delivered",
                }
            )
            ._create_invoices(sale_order_foreign)
        )
        invoices_foreign.action_post()
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                "revenues": {
                    "data": [
                        {
                            "id": "other_revenues_aal",
                            "sequence": sequence_per_invoice_type["other_revenues_aal"],
                            "invoiced": 100.0,
                            "to_invoice": 0.0,
                        },
                        {
                            "id": invoice_type,
                            "sequence": sequence_per_invoice_type[invoice_type],
                            "to_invoice": self.delivery_service_order_line.amount_taxexc_to_invoice,
                            "invoiced": sol_foreign.amount_taxexc_invoiced * 0.2,
                        },
                    ],
                    "total": {
                        "to_invoice": self.delivery_service_order_line.amount_taxexc_to_invoice,
                        "invoiced": 100 + sol_foreign.amount_taxexc_invoiced * 0.2,
                    },
                },
                "costs": {
                    "data": [
                        {
                            "id": "other_costs_aal",
                            "sequence": sequence_per_invoice_type["other_costs_aal"],
                            "billed": -100.0,
                            "to_bill": 0.0,
                        }
                    ],
                    "total": {"billed": -100.0, "to_bill": 0.0},
                },
            },
        )
        self.assertEqual(sol_foreign.qty_invoiced, 1)
        self.assertEqual(sol_foreign.amount_taxexc_to_invoice, 0.0)
        self.assertNotEqual(sol_foreign.amount_taxexc_invoiced, 0.0)

        context = {
            "active_model": "sale.order",
            "active_ids": self.sale_order.ids,
            "active_id": self.sale_order.id,
        }
        invoices = (
            self.env["sale.advance.payment.inv"]
            .with_context(context)
            .create(
                {
                    "advance_payment_method": "delivered",
                }
            )
            ._create_invoices(self.sale_order)
        )
        invoices.action_post()
        invoice_type = service_policy_to_invoice_type[
            self.delivery_service_order_line.product_id.service_policy
        ]
        self.assertIn(
            invoice_type,
            ["billable_manual", "service_revenues"],
            'invoice_type="billable_manual" if sale_timesheet is installed otherwise it is equal to "service_revenues"',
        )
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                "revenues": {
                    "data": [
                        {
                            "id": "other_revenues_aal",
                            "sequence": sequence_per_invoice_type["other_revenues_aal"],
                            "invoiced": 100.0,
                            "to_invoice": 0.0,
                        },
                        {
                            "id": invoice_type,
                            "sequence": sequence_per_invoice_type[invoice_type],
                            "to_invoice": 0.0,
                            "invoiced": self.delivery_service_order_line.amount_taxexc_invoiced
                            + sol_foreign.amount_taxexc_invoiced * 0.2,
                        },
                    ],
                    "total": {
                        "to_invoice": 0.0,
                        "invoiced": self.delivery_service_order_line.amount_taxexc_invoiced
                        + 100
                        + sol_foreign.amount_taxexc_invoiced * 0.2,
                    },
                },
                "costs": {
                    "data": [
                        {
                            "id": "other_costs_aal",
                            "sequence": sequence_per_invoice_type["other_costs_aal"],
                            "billed": -100.0,
                            "to_bill": 0.0,
                        }
                    ],
                    "total": {"billed": -100.0, "to_bill": 0.0},
                },
            },
        )
        self.assertEqual(self.delivery_service_order_line.qty_invoiced, 1)
        self.assertEqual(self.delivery_service_order_line.amount_taxexc_to_invoice, 0.0)
        self.assertNotEqual(
            self.delivery_service_order_line.amount_taxexc_invoiced, 0.0
        )

        SaleOrderLineForeign = self.env["sale.order.line"].with_context(
            tracking_disable=True, default_order_id=sale_order_foreign.id
        )
        manual_service_sol_foreign, material_sol_foreign = SaleOrderLineForeign.create(
            [
                {
                    "product_id": self.product_delivery_service.id,
                    "product_qty": 5,
                    "qty_transferred": 5,
                },
                {
                    "product_id": self.material_product.id,
                    "product_qty": 1,
                    "qty_transferred": 1,
                },
            ]
        )
        service_sols_foreign = sol_foreign + manual_service_sol_foreign
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                "revenues": {
                    "data": [
                        {
                            "id": "other_revenues_aal",
                            "sequence": sequence_per_invoice_type["other_revenues_aal"],
                            "invoiced": 100.0,
                            "to_invoice": 0.0,
                        },
                        {
                            "id": "materials",
                            "sequence": sequence_per_invoice_type["materials"],
                            "to_invoice": material_sol_foreign.amount_taxexc_to_invoice
                            * 0.2,
                            "invoiced": material_sol_foreign.amount_taxexc_invoiced
                            * 0.2,
                        },
                        {
                            "id": invoice_type,
                            "sequence": sequence_per_invoice_type[invoice_type],
                            "to_invoice": sum(
                                service_sols_foreign.mapped("amount_taxexc_to_invoice")
                            )
                            * 0.2,
                            "invoiced": self.delivery_service_order_line.amount_taxexc_invoiced
                            + sum(service_sols_foreign.mapped("amount_taxexc_invoiced"))
                            * 0.2,
                        },
                    ],
                    "total": {
                        "to_invoice": (
                            sum(service_sols_foreign.mapped("amount_taxexc_to_invoice"))
                            + material_sol_foreign.amount_taxexc_to_invoice
                        )
                        * 0.2,
                        "invoiced": self.delivery_service_order_line.amount_taxexc_invoiced
                        + (
                            sum(service_sols_foreign.mapped("amount_taxexc_invoiced"))
                            + material_sol_foreign.amount_taxexc_invoiced
                        )
                        * 0.2
                        + 100,
                    },
                },
                "costs": {
                    "data": [
                        {
                            "id": "other_costs_aal",
                            "sequence": sequence_per_invoice_type["other_costs_aal"],
                            "billed": -100.0,
                            "to_bill": 0.0,
                        }
                    ],
                    "total": {"billed": -100.0, "to_bill": 0.0},
                },
            },
        )
        self.assertNotEqual(manual_service_sol_foreign.amount_taxexc_to_invoice, 0.0)
        self.assertEqual(manual_service_sol_foreign.amount_taxexc_invoiced, 0.0)
        self.assertNotEqual(material_sol_foreign.amount_taxexc_to_invoice, 0.0)
        self.assertEqual(material_sol_foreign.amount_taxexc_invoiced, 0.0)
        SaleOrderLine = self.env["sale.order.line"].with_context(
            tracking_disable=True, default_order_id=self.sale_order.id
        )
        manual_service_order_line = SaleOrderLine.create(
            {
                "product_id": self.product_delivery_service.id,
                "product_qty": 5,
                "qty_transferred": 5,
            }
        )
        material_order_line = SaleOrderLine.create(
            {
                "product_id": self.material_product.id,
                "product_qty": 1,
                "qty_transferred": 1,
            }
        )
        service_sols = self.delivery_service_order_line + manual_service_order_line
        invoice_type = service_policy_to_invoice_type[
            manual_service_order_line.product_id.service_policy
        ]
        self.assertIn(
            invoice_type,
            ["billable_manual", "service_revenues"],
            'invoice_type="billable_manual" if sale_timesheet is installed otherwise it is equal to "service_revenues"',
        )
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                "revenues": {
                    "data": [
                        {
                            "id": "other_revenues_aal",
                            "sequence": sequence_per_invoice_type["other_revenues_aal"],
                            "invoiced": 100.0,
                            "to_invoice": 0.0,
                        },
                        {
                            "id": "materials",
                            "sequence": sequence_per_invoice_type["materials"],
                            "to_invoice": material_order_line.amount_taxexc_to_invoice
                            + material_sol_foreign.amount_taxexc_to_invoice * 0.2,
                            "invoiced": material_order_line.amount_taxexc_invoiced
                            + material_sol_foreign.amount_taxexc_invoiced * 0.2,
                        },
                        {
                            "id": invoice_type,
                            "sequence": sequence_per_invoice_type[invoice_type],
                            "to_invoice": sum(
                                service_sols.mapped("amount_taxexc_to_invoice")
                            )
                            + sum(
                                service_sols_foreign.mapped("amount_taxexc_to_invoice")
                            )
                            * 0.2,
                            "invoiced": sum(
                                service_sols.mapped("amount_taxexc_invoiced")
                            )
                            + sum(service_sols_foreign.mapped("amount_taxexc_invoiced"))
                            * 0.2,
                        },
                    ],
                    "total": {
                        "to_invoice": sum(
                            service_sols.mapped("amount_taxexc_to_invoice")
                        )
                        + material_order_line.amount_taxexc_to_invoice
                        + (
                            sum(service_sols_foreign.mapped("amount_taxexc_to_invoice"))
                            + material_sol_foreign.amount_taxexc_to_invoice
                        )
                        * 0.2,
                        "invoiced": sum(service_sols.mapped("amount_taxexc_invoiced"))
                        + material_order_line.amount_taxexc_invoiced
                        + (
                            sum(service_sols_foreign.mapped("amount_taxexc_invoiced"))
                            + material_sol_foreign.amount_taxexc_invoiced
                        )
                        * 0.2
                        + 100,
                    },
                },
                "costs": {
                    "data": [
                        {
                            "id": "other_costs_aal",
                            "sequence": sequence_per_invoice_type["other_costs_aal"],
                            "billed": -100.0,
                            "to_bill": 0.0,
                        }
                    ],
                    "total": {"billed": -100.0, "to_bill": 0.0},
                },
            },
        )
        self.assertNotEqual(manual_service_order_line.amount_taxexc_to_invoice, 0.0)
        self.assertEqual(manual_service_order_line.amount_taxexc_invoiced, 0.0)
        self.assertNotEqual(material_order_line.amount_taxexc_to_invoice, 0.0)
        self.assertEqual(material_order_line.amount_taxexc_invoiced, 0.0)

        credit_notes = invoices_foreign._reverse_moves()
        credit_notes.action_post()
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                "revenues": {
                    "data": [
                        {
                            "id": "other_revenues_aal",
                            "sequence": sequence_per_invoice_type["other_revenues_aal"],
                            "invoiced": 100.0,
                            "to_invoice": 0.0,
                        },
                        {
                            "id": "materials",
                            "sequence": sequence_per_invoice_type["materials"],
                            "to_invoice": material_order_line.amount_taxexc_to_invoice
                            + material_sol_foreign.amount_taxexc_to_invoice * 0.2,
                            "invoiced": material_order_line.amount_taxexc_invoiced
                            + material_sol_foreign.amount_taxexc_invoiced * 0.2,
                        },
                        {
                            "id": invoice_type,
                            "sequence": sequence_per_invoice_type[invoice_type],
                            "to_invoice": sum(
                                service_sols.mapped("amount_taxexc_to_invoice")
                            )
                            + sum(
                                service_sols_foreign.mapped("amount_taxexc_to_invoice")
                            )
                            * 0.2,
                            "invoiced": sum(
                                service_sols.mapped("amount_taxexc_invoiced")
                            )
                            + sum(service_sols_foreign.mapped("amount_taxexc_invoiced"))
                            * 0.2,
                        },
                    ],
                    "total": {
                        "to_invoice": sum(
                            service_sols.mapped("amount_taxexc_to_invoice")
                        )
                        + material_order_line.amount_taxexc_to_invoice
                        + (
                            sum(service_sols_foreign.mapped("amount_taxexc_to_invoice"))
                            + material_sol_foreign.amount_taxexc_to_invoice
                        )
                        * 0.2,
                        "invoiced": sum(service_sols.mapped("amount_taxexc_invoiced"))
                        + material_order_line.amount_taxexc_invoiced
                        + (
                            sum(service_sols_foreign.mapped("amount_taxexc_invoiced"))
                            + material_sol_foreign.amount_taxexc_invoiced
                        )
                        * 0.2
                        + 100,
                    },
                },
                "costs": {
                    "data": [
                        {
                            "id": "other_costs_aal",
                            "sequence": sequence_per_invoice_type["other_costs_aal"],
                            "billed": -100.0,
                            "to_bill": 0.0,
                        }
                    ],
                    "total": {"billed": -100.0, "to_bill": 0.0},
                },
            },
        )
        self.assertEqual(sol_foreign.qty_invoiced, 0.0)
        self.assertNotEqual(sol_foreign.amount_taxexc_to_invoice, 0.0)
        self.assertEqual(sol_foreign.amount_taxexc_invoiced, 0.0)

        credit_notes = invoices._reverse_moves()
        credit_notes.action_post()
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                "revenues": {
                    "data": [
                        {
                            "id": "other_revenues_aal",
                            "sequence": sequence_per_invoice_type["other_revenues_aal"],
                            "invoiced": 100.0,
                            "to_invoice": 0.0,
                        },
                        {
                            "id": "materials",
                            "sequence": sequence_per_invoice_type["materials"],
                            "to_invoice": material_order_line.amount_taxexc_to_invoice
                            + material_sol_foreign.amount_taxexc_to_invoice * 0.2,
                            "invoiced": material_order_line.amount_taxexc_invoiced
                            + material_sol_foreign.amount_taxexc_invoiced * 0.2,
                        },
                        {
                            "id": invoice_type,
                            "sequence": sequence_per_invoice_type[invoice_type],
                            "to_invoice": sum(
                                service_sols.mapped("amount_taxexc_to_invoice")
                            )
                            + sum(
                                service_sols_foreign.mapped("amount_taxexc_to_invoice")
                            )
                            * 0.2,
                            "invoiced": sum(
                                service_sols.mapped("amount_taxexc_invoiced")
                            )
                            + sum(service_sols_foreign.mapped("amount_taxexc_invoiced"))
                            * 0.2,
                        },
                    ],
                    "total": {
                        "to_invoice": sum(
                            service_sols.mapped("amount_taxexc_to_invoice")
                        )
                        + material_order_line.amount_taxexc_to_invoice
                        + (
                            sum(service_sols_foreign.mapped("amount_taxexc_to_invoice"))
                            + material_sol_foreign.amount_taxexc_to_invoice
                        )
                        * 0.2,
                        "invoiced": sum(service_sols.mapped("amount_taxexc_invoiced"))
                        + material_order_line.amount_taxexc_invoiced
                        + (
                            sum(service_sols_foreign.mapped("amount_taxexc_invoiced"))
                            + material_sol_foreign.amount_taxexc_invoiced
                        )
                        * 0.2
                        + 100,
                    },
                },
                "costs": {
                    "data": [
                        {
                            "id": "other_costs_aal",
                            "sequence": sequence_per_invoice_type["other_costs_aal"],
                            "billed": -100.0,
                            "to_bill": 0.0,
                        }
                    ],
                    "total": {"billed": -100.0, "to_bill": 0.0},
                },
            },
        )
        self.assertEqual(self.delivery_service_order_line.qty_invoiced, 0.0)
        self.assertNotEqual(
            self.delivery_service_order_line.amount_taxexc_to_invoice, 0.0
        )
        self.assertEqual(self.delivery_service_order_line.amount_taxexc_invoiced, 0.0)

        sale_order_foreign._action_cancel()
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                "revenues": {
                    "data": [
                        {
                            "id": "other_revenues_aal",
                            "sequence": sequence_per_invoice_type["other_revenues_aal"],
                            "invoiced": 100.0,
                            "to_invoice": 0.0,
                        },
                        {
                            "id": "materials",
                            "sequence": sequence_per_invoice_type["materials"],
                            "to_invoice": material_order_line.amount_taxexc_to_invoice,
                            "invoiced": material_order_line.amount_taxexc_invoiced,
                        },
                        {
                            "id": invoice_type,
                            "sequence": sequence_per_invoice_type[invoice_type],
                            "to_invoice": sum(
                                service_sols.mapped("amount_taxexc_to_invoice")
                            ),
                            "invoiced": sum(
                                service_sols.mapped("amount_taxexc_invoiced")
                            ),
                        },
                    ],
                    "total": {
                        "to_invoice": sum(
                            service_sols.mapped("amount_taxexc_to_invoice")
                        )
                        + material_order_line.amount_taxexc_to_invoice,
                        "invoiced": sum(service_sols.mapped("amount_taxexc_invoiced"))
                        + material_order_line.amount_taxexc_invoiced
                        + 100,
                    },
                },
                "costs": {
                    "data": [
                        {
                            "id": "other_costs_aal",
                            "sequence": sequence_per_invoice_type["other_costs_aal"],
                            "billed": -100.0,
                            "to_bill": 0.0,
                        }
                    ],
                    "total": {"billed": -100.0, "to_bill": 0.0},
                },
            },
        )
        Downpayment = {
            "active_model": "sale.order",
            "active_ids": self.sale_order.ids,
            "active_id": self.sale_order.id,
            "default_journal_id": self.company_data["default_journal_sale"].id,
        }
        downpayment = (
            self.env["sale.advance.payment.inv"]
            .with_context(Downpayment)
            .create(
                {
                    "advance_payment_method": "fixed",
                    "fixed_amount": 115,
                }
            )
        )
        down_payment_invoiced = 100.00
        downpayment.create_invoices()
        self.sale_order.invoice_ids[2].action_post()
        self._assert_dict_equal(
            invoice_type,
            sequence_per_invoice_type,
            material_order_line,
            service_sols,
            manual_service_order_line,
            down_payment_invoiced,
        )

        downpayment = (
            self.env["sale.advance.payment.inv"]
            .with_context(Downpayment)
            .create(
                {
                    "advance_payment_method": "fixed",
                    "fixed_amount": 115,
                }
            )
        )
        down_payment_invoiced *= 2
        downpayment.create_invoices()
        self.sale_order.invoice_ids[3].action_post()
        self._assert_dict_equal(
            invoice_type,
            sequence_per_invoice_type,
            material_order_line,
            service_sols,
            manual_service_order_line,
            down_payment_invoiced,
        )

        for sol in sale_order_foreign.line_ids:
            self.assertEqual(sol.amount_taxexc_to_invoice, 0.0)
            self.assertEqual(sol.amount_taxexc_invoiced, 0.0)

        self.sale_order._action_cancel()
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                "revenues": {
                    "data": [
                        {
                            "id": "other_revenues_aal",
                            "sequence": sequence_per_invoice_type["other_revenues_aal"],
                            "invoiced": 100.0,
                            "to_invoice": 0.0,
                        }
                    ],
                    "total": {"to_invoice": 0.0, "invoiced": 100},
                },
                "costs": {
                    "data": [
                        {
                            "id": "other_costs_aal",
                            "sequence": sequence_per_invoice_type["other_costs_aal"],
                            "billed": -100.0,
                            "to_bill": 0.0,
                        }
                    ],
                    "total": {"billed": -100.0, "to_bill": 0.0},
                },
            },
        )
        for sol in self.sale_order.line_ids:
            if sol.is_downpayment:
                continue
            self.assertEqual(sol.amount_taxexc_to_invoice, 0.0)
            self.assertEqual(sol.amount_taxexc_invoiced, 0.0)

    def _assert_dict_equal(
        self,
        invoice_type,
        sequence_per_invoice_type,
        material_order_line,
        service_sols,
        manual_service_order_line,
        down_payment_invoiced,
    ):
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                "revenues": {
                    "data": [
                        {
                            "id": "other_revenues_aal",
                            "sequence": sequence_per_invoice_type["other_revenues_aal"],
                            "invoiced": 100.0,
                            "to_invoice": 0.0,
                        },
                        {
                            "id": "downpayments",
                            "sequence": 20,
                            "invoiced": down_payment_invoiced,
                            "to_invoice": -down_payment_invoiced,
                        },
                        {
                            "id": "materials",
                            "sequence": sequence_per_invoice_type["materials"],
                            "invoiced": material_order_line.amount_taxexc_invoiced,
                            "to_invoice": material_order_line.amount_taxexc_to_invoice,
                        },
                        {
                            "id": invoice_type,
                            "sequence": sequence_per_invoice_type[invoice_type],
                            "invoiced": manual_service_order_line.amount_taxexc_invoiced,
                            "to_invoice": sum(
                                service_sols.mapped("amount_taxexc_to_invoice")
                            ),
                        },
                    ],
                    "total": {
                        "invoiced": manual_service_order_line.amount_taxexc_invoiced
                        + material_order_line.amount_taxexc_invoiced
                        + down_payment_invoiced
                        + 100,
                        "to_invoice": sum(
                            service_sols.mapped("amount_taxexc_to_invoice")
                        )
                        + material_order_line.amount_taxexc_to_invoice
                        - down_payment_invoiced,
                    },
                },
                "costs": {
                    "data": [
                        {
                            "id": "other_costs_aal",
                            "sequence": sequence_per_invoice_type["other_costs_aal"],
                            "billed": -100.0,
                            "to_bill": 0.0,
                        }
                    ],
                    "total": {"billed": -100.0, "to_bill": 0.0},
                },
            },
        )

    def test_invoices_without_sale_order_are_accounted_in_profitability(self):
        foreign_company = self.company_data_2["company"]
        foreign_company.currency_id = self.foreign_currency
        analytic_distribution = 50
        analytic_contribution = analytic_distribution / 100.0
        invoice_1_foreign = self.env["account.move"].create(
            {
                "name": "Invoice_1",
                "move_type": "out_invoice",
                "state": "draft",
                "partner_id": self.partner.id,
                "invoice_date": datetime.today(),
                "company_id": foreign_company.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "analytic_distribution": {
                                self.project_billable_no_company.account_id.id: analytic_distribution
                            },
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "product_uom_id": self.product_a.uom_id.id,
                            "price_unit": self.product_a.standard_price,
                            "currency_id": self.foreign_currency.id,
                        }
                    )
                ],
            }
        )
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)[
                "revenues"
            ],
            {
                "data": [
                    {
                        "id": "other_invoice_revenues",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_invoice_revenues"
                        ],
                        "to_invoice": self.product_a.standard_price
                        * analytic_contribution
                        * 0.2,
                        "invoiced": 0.0,
                    }
                ],
                "total": {
                    "to_invoice": self.product_a.standard_price
                    * analytic_contribution
                    * 0.2,
                    "invoiced": 0.0,
                },
            },
        )
        invoice_1 = self.env["account.move"].create(
            {
                "name": "Invoice_1",
                "move_type": "out_invoice",
                "state": "draft",
                "partner_id": self.partner.id,
                "invoice_date": datetime.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "analytic_distribution": {
                                self.project_billable_no_company.account_id.id: analytic_distribution
                            },
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "product_uom_id": self.product_a.uom_id.id,
                            "price_unit": self.product_a.standard_price,
                        }
                    )
                ],
            }
        )
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)[
                "revenues"
            ],
            {
                "data": [
                    {
                        "id": "other_invoice_revenues",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_invoice_revenues"
                        ],
                        "to_invoice": self.product_a.standard_price
                        * analytic_contribution
                        * 1.2,
                        "invoiced": 0.0,
                    }
                ],
                "total": {
                    "to_invoice": self.product_a.standard_price
                    * analytic_contribution
                    * 1.2,
                    "invoiced": 0.0,
                },
            },
        )
        invoice_1.action_post()
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)[
                "revenues"
            ],
            {
                "data": [
                    {
                        "id": "other_invoice_revenues",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_invoice_revenues"
                        ],
                        "to_invoice": self.product_a.standard_price
                        * analytic_contribution
                        * 0.2,
                        "invoiced": self.product_a.standard_price
                        * analytic_contribution,
                    }
                ],
                "total": {
                    "to_invoice": self.product_a.standard_price
                    * analytic_contribution
                    * 0.2,
                    "invoiced": self.product_a.standard_price * analytic_contribution,
                },
            },
        )
        invoice_1_foreign.action_post()
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)[
                "revenues"
            ],
            {
                "data": [
                    {
                        "id": "other_invoice_revenues",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_invoice_revenues"
                        ],
                        "to_invoice": 0.0,
                        "invoiced": self.product_a.standard_price
                        * analytic_contribution
                        * 1.2,
                    }
                ],
                "total": {
                    "to_invoice": 0.0,
                    "invoiced": self.product_a.standard_price
                    * analytic_contribution
                    * 1.2,
                },
            },
        )

        NEG_AMOUNT = -42
        invoice_2 = self.env["account.move"].create(
            {
                "name": "I have 2 lines",
                "move_type": "out_invoice",
                "state": "draft",
                "partner_id": self.partner.id,
                "invoice_date": datetime.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "analytic_distribution": {
                                self.project_billable_no_company.account_id.id: analytic_distribution
                            },
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "product_uom_id": self.product_a.uom_id.id,
                            "price_unit": self.product_a.standard_price,
                        }
                    ),
                    Command.create(
                        {
                            "analytic_distribution": {
                                self.project_billable_no_company.account_id.id: analytic_distribution
                            },
                            "product_id": self.product_b.id,
                            "quantity": 2,
                            "product_uom_id": self.product_b.uom_id.id,
                            "price_unit": self.product_b.standard_price,
                        }
                    ),
                    Command.create(
                        {
                            "analytic_distribution": {
                                self.project_billable_no_company.account_id.id: analytic_distribution
                            },
                            "product_id": self.product_b.id,
                            "quantity": 1,
                            "product_uom_id": self.product_b.uom_id.id,
                            "price_unit": NEG_AMOUNT,
                        }
                    ),
                ],
            }
        )
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)[
                "revenues"
            ],
            {
                "data": [
                    {
                        "id": "other_invoice_revenues",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_invoice_revenues"
                        ],
                        "to_invoice": (
                            self.product_a.standard_price
                            + 2 * self.product_b.standard_price
                            + NEG_AMOUNT
                        )
                        * analytic_contribution,
                        "invoiced": self.product_a.standard_price
                        * analytic_contribution
                        * 1.2,
                    }
                ],
                "total": {
                    "to_invoice": (
                        self.product_a.standard_price
                        + 2 * self.product_b.standard_price
                        + NEG_AMOUNT
                    )
                    * analytic_contribution,
                    "invoiced": self.product_a.standard_price
                    * analytic_contribution
                    * 1.2,
                },
            },
        )
        invoice_2.action_post()
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)[
                "revenues"
            ],
            {
                "data": [
                    {
                        "id": "other_invoice_revenues",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_invoice_revenues"
                        ],
                        "to_invoice": 0.0,
                        "invoiced": (
                            2.2 * self.product_a.standard_price
                            + 2 * self.product_b.standard_price
                            + NEG_AMOUNT
                        )
                        * analytic_contribution,
                    }
                ],
                "total": {
                    "to_invoice": 0.0,
                    "invoiced": (
                        2.2 * self.product_a.standard_price
                        + 2 * self.product_b.standard_price
                        + NEG_AMOUNT
                    )
                    * analytic_contribution,
                },
            },
        )
        invoice_2_foreign = self.env["account.move"].create(
            {
                "name": "I have 2 lines",
                "move_type": "out_invoice",
                "state": "draft",
                "partner_id": self.partner.id,
                "invoice_date": datetime.today(),
                "company_id": foreign_company.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "analytic_distribution": {
                                self.project_billable_no_company.account_id.id: analytic_distribution
                            },
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "product_uom_id": self.product_a.uom_id.id,
                            "price_unit": self.product_a.standard_price,
                            "currency_id": self.foreign_currency.id,
                        }
                    ),
                    Command.create(
                        {
                            "analytic_distribution": {
                                self.project_billable_no_company.account_id.id: analytic_distribution
                            },
                            "product_id": self.product_b.id,
                            "quantity": 2,
                            "product_uom_id": self.product_b.uom_id.id,
                            "price_unit": self.product_b.standard_price,
                            "currency_id": self.foreign_currency.id,
                        }
                    ),
                ],
            }
        )
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)[
                "revenues"
            ],
            {
                "data": [
                    {
                        "id": "other_invoice_revenues",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_invoice_revenues"
                        ],
                        "to_invoice": (
                            self.product_a.standard_price
                            + 2 * self.product_b.standard_price
                        )
                        * analytic_contribution
                        * 0.2,
                        "invoiced": (
                            2.2 * self.product_a.standard_price
                            + 2 * self.product_b.standard_price
                            + NEG_AMOUNT
                        )
                        * analytic_contribution,
                    }
                ],
                "total": {
                    "to_invoice": (
                        self.product_a.standard_price
                        + 2 * self.product_b.standard_price
                    )
                    * analytic_contribution
                    * 0.2,
                    "invoiced": (
                        2.2 * self.product_a.standard_price
                        + 2 * self.product_b.standard_price
                        + NEG_AMOUNT
                    )
                    * analytic_contribution,
                },
            },
        )
        invoice_2_foreign.action_post()
        items = self.project_billable_no_company._get_profitability_items(False)[
            "revenues"
        ]
        self.assertEqual(
            float_compare(
                (
                    (self.product_a.standard_price + self.product_b.standard_price)
                    * 2.4
                    + NEG_AMOUNT
                )
                * analytic_contribution,
                items["data"][0]["invoiced"],
                2,
            ),
            0,
        )
        self.assertEqual(
            float_compare(
                (
                    (self.product_a.standard_price + self.product_b.standard_price)
                    * 2.4
                    + NEG_AMOUNT
                )
                * analytic_contribution,
                items["total"]["invoiced"],
                2,
            ),
            0,
        )
        self.assertEqual(items["data"][0]["id"], "other_invoice_revenues")
        self.assertEqual(
            items["data"][0]["sequence"],
            self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                "other_invoice_revenues"
            ],
        )
        self.assertEqual(items["data"][0]["to_invoice"], 0.0)
        self.assertEqual(items["total"]["to_invoice"], 0.0)

    def test_bills_without_purchase_order_are_accounted_in_profitability_sale_project(
        self,
    ):
        foreign_company = self.company_data_2["company"]
        foreign_company.currency_id = self.foreign_currency

        bill_1_foreign = self.env["account.move"].create(
            {
                "name": "Bill_1 name",
                "move_type": "in_invoice",
                "state": "draft",
                "partner_id": self.partner.id,
                "invoice_date": datetime.today(),
                "company_id": foreign_company.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "analytic_distribution": {
                                self.project_billable_no_company.account_id.id: 100
                            },
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "product_uom_id": self.product_a.uom_id.id,
                            "price_unit": self.product_a.standard_price,
                            "currency_id": self.foreign_currency.id,
                        }
                    )
                ],
            }
        )
        self.env["account.analytic.line"].create(
            [
                {
                    "name": "extra costs 1",
                    "account_id": self.project_billable_no_company.account_id.id,
                    "amount": -50,
                },
                {
                    "name": "extra costs 2",
                    "account_id": self.project_billable_no_company.account_id.id,
                    "amount": -100,
                },
            ]
        )
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)["costs"],
            {
                "data": [
                    {
                        "id": "other_costs_aal",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_costs_aal"
                        ],
                        "to_bill": 0.0,
                        "billed": -150.0,
                    },
                    {
                        "id": "other_purchase_costs",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_purchase_costs"
                        ],
                        "to_bill": -self.product_a.standard_price * 0.2,
                        "billed": 0.0,
                    },
                ],
                "total": {
                    "to_bill": -self.product_a.standard_price * 0.2,
                    "billed": -150.0,
                },
            },
        )
        bill_1 = self.env["account.move"].create(
            {
                "name": "Bill_1 name",
                "move_type": "in_invoice",
                "state": "draft",
                "partner_id": self.partner.id,
                "invoice_date": datetime.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "analytic_distribution": {
                                self.project_billable_no_company.account_id.id: 100
                            },
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "product_uom_id": self.product_a.uom_id.id,
                            "price_unit": self.product_a.standard_price,
                        }
                    )
                ],
            }
        )
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)["costs"],
            {
                "data": [
                    {
                        "id": "other_costs_aal",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_costs_aal"
                        ],
                        "to_bill": 0.0,
                        "billed": -150.0,
                    },
                    {
                        "id": "other_purchase_costs",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_purchase_costs"
                        ],
                        "to_bill": -self.product_a.standard_price * 1.2,
                        "billed": 0.0,
                    },
                ],
                "total": {
                    "to_bill": -self.product_a.standard_price * 1.2,
                    "billed": -150.0,
                },
            },
        )
        bill_1.action_post()
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)["costs"],
            {
                "data": [
                    {
                        "id": "other_costs_aal",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_costs_aal"
                        ],
                        "to_bill": 0.0,
                        "billed": -150.0,
                    },
                    {
                        "id": "other_purchase_costs",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_purchase_costs"
                        ],
                        "to_bill": -self.product_a.standard_price * 0.2,
                        "billed": -self.product_a.standard_price,
                    },
                ],
                "total": {
                    "to_bill": -self.product_a.standard_price * 0.2,
                    "billed": -self.product_a.standard_price - 150,
                },
            },
        )
        bill_1_foreign.action_post()
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)["costs"],
            {
                "data": [
                    {
                        "id": "other_costs_aal",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_costs_aal"
                        ],
                        "to_bill": 0.0,
                        "billed": -150.0,
                    },
                    {
                        "id": "other_purchase_costs",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_purchase_costs"
                        ],
                        "to_bill": 0.0,
                        "billed": -self.product_a.standard_price * 1.2,
                    },
                ],
                "total": {
                    "to_bill": 0.0,
                    "billed": -self.product_a.standard_price * 1.2 - 150,
                },
            },
        )
        bill_2 = self.env["account.move"].create(
            {
                "name": "I have 2 lines",
                "move_type": "in_invoice",
                "state": "draft",
                "partner_id": self.partner.id,
                "invoice_date": datetime.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "analytic_distribution": {
                                self.project_billable_no_company.account_id.id: 100
                            },
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "product_uom_id": self.product_a.uom_id.id,
                            "price_unit": self.product_a.standard_price,
                        }
                    ),
                    Command.create(
                        {
                            "analytic_distribution": {
                                self.project_billable_no_company.account_id.id: 100
                            },
                            "product_id": self.product_b.id,
                            "quantity": 2,
                            "product_uom_id": self.product_b.uom_id.id,
                            "price_unit": self.product_b.standard_price,
                        }
                    ),
                ],
            }
        )
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)["costs"],
            {
                "data": [
                    {
                        "id": "other_costs_aal",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_costs_aal"
                        ],
                        "to_bill": 0.0,
                        "billed": -150.0,
                    },
                    {
                        "id": "other_purchase_costs",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_purchase_costs"
                        ],
                        "to_bill": -(
                            self.product_a.standard_price
                            + 2 * self.product_b.standard_price
                        ),
                        "billed": -self.product_a.standard_price * 1.2,
                    },
                ],
                "total": {
                    "to_bill": -(
                        self.product_a.standard_price
                        + 2 * self.product_b.standard_price
                    ),
                    "billed": -self.product_a.standard_price * 1.2 - 150,
                },
            },
        )
        bill_2.action_post()
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)["costs"],
            {
                "data": [
                    {
                        "id": "other_costs_aal",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_costs_aal"
                        ],
                        "to_bill": 0.0,
                        "billed": -150.0,
                    },
                    {
                        "id": "other_purchase_costs",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_purchase_costs"
                        ],
                        "to_bill": 0.0,
                        "billed": -(
                            2.2 * self.product_a.standard_price
                            + 2 * self.product_b.standard_price
                        ),
                    },
                ],
                "total": {
                    "to_bill": 0.0,
                    "billed": -(
                        2.2 * self.product_a.standard_price
                        + 2 * self.product_b.standard_price
                    )
                    - 150,
                },
            },
        )
        bill_2_foreign = self.env["account.move"].create(
            {
                "name": "I have 2 lines",
                "move_type": "in_invoice",
                "state": "draft",
                "partner_id": self.partner.id,
                "invoice_date": datetime.today(),
                "company_id": foreign_company.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "analytic_distribution": {
                                self.project_billable_no_company.account_id.id: 100
                            },
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "product_uom_id": self.product_a.uom_id.id,
                            "price_unit": self.product_a.standard_price,
                            "currency_id": self.foreign_currency.id,
                        }
                    ),
                    Command.create(
                        {
                            "analytic_distribution": {
                                self.project_billable_no_company.account_id.id: 100
                            },
                            "product_id": self.product_b.id,
                            "quantity": 2,
                            "product_uom_id": self.product_b.uom_id.id,
                            "price_unit": self.product_b.standard_price,
                            "currency_id": self.foreign_currency.id,
                        }
                    ),
                ],
            }
        )
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)["costs"],
            {
                "data": [
                    {
                        "id": "other_costs_aal",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_costs_aal"
                        ],
                        "to_bill": 0.0,
                        "billed": -150.0,
                    },
                    {
                        "id": "other_purchase_costs",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_purchase_costs"
                        ],
                        "to_bill": -(
                            self.product_a.standard_price
                            + 2 * self.product_b.standard_price
                        )
                        * 0.2,
                        "billed": -(
                            2.2 * self.product_a.standard_price
                            + 2 * self.product_b.standard_price
                        ),
                    },
                ],
                "total": {
                    "to_bill": -(
                        self.product_a.standard_price
                        + 2 * self.product_b.standard_price
                    )
                    * 0.2,
                    "billed": -(
                        2.2 * self.product_a.standard_price
                        + 2 * self.product_b.standard_price
                    )
                    - 150,
                },
            },
        )
        bill_2_foreign.action_post()
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)["costs"],
            {
                "data": [
                    {
                        "id": "other_costs_aal",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_costs_aal"
                        ],
                        "to_bill": 0.0,
                        "billed": -150.0,
                    },
                    {
                        "id": "other_purchase_costs",
                        "sequence": self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                            "other_purchase_costs"
                        ],
                        "to_bill": 0.0,
                        "billed": -2.4
                        * (
                            self.product_a.standard_price
                            + self.product_b.standard_price
                        ),
                    },
                ],
                "total": {
                    "to_bill": 0.0,
                    "billed": -2.4
                    * (self.product_a.standard_price + self.product_b.standard_price)
                    - 150,
                },
            },
        )
