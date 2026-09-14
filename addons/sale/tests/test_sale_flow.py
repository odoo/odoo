from odoo.addons.sale.tests.common import TestSaleCommon


class TestSaleFlow(TestSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        user = cls.env["res.users"].create(
            {
                "name": "Because I am saleman!",
                "login": "saleman",
                "group_ids": [
                    (6, 0, cls.env.user.group_ids.ids),
                    (4, cls.env.ref("account.group_account_user").id),
                ],
            }
        )
        user.partner_id.email = "saleman@test.com"

        cls.env = cls.env(user=user)
        cls.cr = cls.env.cr

        cls.partner_a = cls.env["res.partner"].create(
            {
                "name": "partner_a",
                "company_id": False,
            }
        )

        cls.analytic_plan = cls.env["account.analytic.plan"].create(
            {
                "name": "Plan",
            }
        )

        cls.analytic_account = cls.env["account.analytic.account"].create(
            {
                "name": "Test analytic_account",
                "code": "analytic_account",
                "plan_id": cls.analytic_plan.id,
                "company_id": cls.company.id,
                "partner_id": cls.partner_a.id,
            }
        )

        user.company_ids |= cls.company
        user.company_id = cls.company

    def test_qty_transferred(self):
        # pins the sale-alone behavior: a written transferred quantity of a
        # stock_move line survives confirmation while no module provides it
        if self.env["ir.module.module"]._get("sale_stock").state == "installed":
            self.skipTest("sale_stock computes the transferred quantity from moves")
        sale_order = (
            self.env["sale.order"]
            .with_context(mail_notrack=True, mail_create_nolog=True)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "partner_invoice_id": self.partner_a.id,
                    "partner_shipping_id": self.partner_a.id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": self.company_data["product_order_cost"].name,
                                "product_id": self.company_data[
                                    "product_order_cost"
                                ].id,
                                "product_qty": 2,
                                "qty_transferred": 1,
                                "price_unit": self.company_data[
                                    "product_order_cost"
                                ].list_price,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "name": self.company_data["product_delivery_cost"].name,
                                "product_id": self.company_data[
                                    "product_delivery_cost"
                                ].id,
                                "product_qty": 4,
                                "qty_transferred": 1,
                                "price_unit": self.company_data[
                                    "product_delivery_cost"
                                ].list_price,
                            },
                        ),
                    ],
                }
            )
        )

        sale_order.action_confirm()

        self.assertRecordValues(
            sale_order.line_ids,
            [
                {"qty_transferred": 1.0},
                {"qty_transferred": 1.0},
            ],
        )
