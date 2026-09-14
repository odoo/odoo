from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.sale_purchase.tests.common import TestSalePurchaseCommon


@tagged("-at_install", "post_install")
class TestAccessRights(TestSalePurchaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        group_sale_user = cls.env.ref("sale.group_sale_salesman")
        group_purchase_user = cls.env.ref("purchase.group_purchase_user")
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
        cls.user_purchaseperson = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Jean-Luc Fonck",
                    "login": "jl.fonck",
                    "email": "jl.fonck@chansonbelge.com",
                    "group_ids": [(6, 0, [group_purchase_user.id])],
                }
            )
        )

    def test_access_saleperson(self):
        SaleOrder = self.env["sale.order"].with_context(tracking_disable=True)

        sale_order = SaleOrder.with_user(self.user_salesperson).create(
            {"partner_id": self.partner_a.id, "user_id": self.user_salesperson.id}
        )

        sol_service_purchase = (
            self.env["sale.order.line"]
            .with_user(self.user_salesperson)
            .create(
                {
                    "product_id": self.service_purchase_1.id,
                    "product_qty": 4,
                    "order_id": sale_order.id,
                    "tax_ids": False,
                }
            )
        )

        sale_order.action_confirm()
        sale_order._action_cancel()

        self.assertTrue(sale_order.name, "Saleperson can read its own SO")

        action = sale_order.sudo().action_view_purchase_orders()

        with self.assertRaises(AccessError):
            purchase_orders = (
                self.env["purchase.order"]
                .with_user(self.user_salesperson)
                .browse(action["res_id"])
            )
            purchase_orders.read()

        purchase_orders = (
            self.env["purchase.order"]
            .with_user(self.user_purchaseperson)
            .browse(action["res_id"])
        )
        purchase_orders.read()

        with self.assertRaises(AccessError):
            sol_service_purchase.with_user(
                self.user_salesperson
            ).purchase_line_ids.read()
