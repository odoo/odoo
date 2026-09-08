from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.sale_purchase.tests.common import TestSalePurchaseCommon


@tagged("post_install", "-at_install")
class TestAccessRights(TestSalePurchaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        group_sale_user = cls.env.ref("sale.group_sale_salesman")

        cls.user_salesperson = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Le Grand Jojo User",
                    "login": "grand.jojo",
                    "email": "grand.jojo@chansonbelge.com",
                    "group_ids": [(6, 0, [group_sale_user.id])],
                }
            )
        )

    def test_access_saleperson_decreases_qty(self):
        mto_route = self.env.ref("stock.route_warehouse0_mto")
        buy_route = self.env.ref("purchase_stock.route_warehouse0_buy")
        mto_route.rule_ids.procure_method = "make_to_order"
        mto_route.active = True

        vendor = self.env["res.partner"].create({"name": "vendor"})

        product = self.env["product.product"].create(
            {
                "name": "SuperProduct",
                "is_storable": True,
                "seller_ids": [
                    Command.create(
                        {
                            "partner_id": vendor.id,
                            "price": 8,
                        }
                    )
                ],
                "route_ids": [(6, 0, (mto_route + buy_route).ids)],
            }
        )

        so = (
            self.env["sale.order"]
            .with_user(self.user_salesperson)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "user_id": self.user_salesperson.id,
                }
            )
        )
        so_line, _ = self.env["sale.order.line"].create(
            [
                {
                    "name": product.name,
                    "product_id": product.id,
                    "product_qty": 1,
                    "price_unit": product.list_price,
                    "tax_ids": False,
                    "order_id": so.id,
                },
                {
                    "name": "Super Section",
                    "display_type": "line_section",
                    "order_id": so.id,
                },
            ]
        )

        so.action_confirm()

        po = self.env["purchase.order"].search([("partner_id", "=", vendor.id)])
        po.action_confirm()

        so.write({"line_ids": [(1, so_line.id, {"product_qty": 0.9})]})

        self.assertIn(so.name, po.activity_ids.note)

    def test_access_saleperson_with_orderpoint(self):
        product = self.env["product.product"].create(
            {
                "name": "SuperProduct",
                "is_storable": True,
                "seller_ids": [
                    Command.create(
                        {
                            "partner_id": self.partner_a.id,
                            "price": 8,
                        }
                    )
                ],
            }
        )
        self.env["stock.warehouse.orderpoint"].create(
            {
                "name": "orderpoint test",
                "product_id": product.id,
                "product_min_qty": 0,
                "product_max_qty": 0,
                "route_id": self.env.ref("purchase_stock.route_warehouse0_buy").id,
            }
        )
        so = (
            self.env["sale.order"]
            .with_user(self.user_salesperson)
            .create(
                {
                    "partner_id": self.partner_b.id,
                    "user_id": self.user_salesperson.id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": product.id,
                                "product_qty": 10,
                                "price_unit": product.list_price,
                            },
                        )
                    ],
                }
            )
        )
        so.action_confirm()
        po = self.env["purchase.order"].search([("partner_id", "=", self.partner_a.id)])
        self.assertEqual(po.line_ids[0].product_qty, 10)
        so.line_ids = [
            Command.create(
                {
                    "product_id": product.id,
                    "product_qty": 11,
                    "price_unit": product.list_price,
                }
            )
        ]

        self.assertEqual(po.line_ids[0].product_qty, 21)
        po.action_confirm()
        self.assertEqual(po.state, "done")

    def test_purchase_user_sees_dest_address_id(self):
        """
        A purchase-only user (no sales role) must still see `dest_address_id`
        on the purchase order form: it is a purchasing field (where goods are
        shipped to), not a sales-only concern.
        """
        group_purchase_user = self.env.ref("purchase.group_purchase_user")
        user_purchase = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Purchase Only User",
                    "login": "purchase.only",
                    "email": "purchase.only@supercompany.com",
                    "group_ids": [(6, 0, [group_purchase_user.id])],
                }
            )
        )
        arch = (
            self.env["purchase.order"]
            .with_user(user_purchase)
            .get_view(view_type="form")["arch"]
        )
        self.assertIn('name="dest_address_id"', arch)

    def test_sales_user_can_access_forecast_report(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": "test",
                            "product_id": self.product.id,
                            "product_qty": 1,
                            "product_uom_id": self.product.uom_id.id,
                        }
                    )
                ],
            }
        )
        different_company_po = self.env["purchase.order"].create(
            {
                "company_id": self.env["res.company"]
                .create({"name": "Different Company"})
                .id,
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": "test",
                            "product_id": self.product.id,
                            "product_qty": 2,
                            "product_uom_id": self.product.uom_id.id,
                        }
                    )
                ],
            }
        )
        po.env.invalidate_all()
        different_company_po.env.invalidate_all()
        report_values = (
            self.env["stock.forecasted_product_product"]
            .with_user(self.user_salesperson)
            .get_report_values(docids=self.product.ids)
        )
        self.assertEqual(report_values["docs"]["user_can_edit_pickings"], False)
        self.assertEqual(
            report_values["docs"]["product"][self.product.id]["draft_purchase_qty"][
                "in"
            ],
            1,
        )
        self.assertEqual(
            report_values["docs"]["product"][self.product.id]["draft_purchase_orders"],
            [{"id": po.id, "name": po.name}],
        )
        with self.assertRaises(
            AccessError, msg="Sales user is not allowed to access a PO"
        ):
            po.with_user(self.user_salesperson).action_confirm()
