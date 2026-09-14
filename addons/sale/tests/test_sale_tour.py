from odoo.fields import Command
from odoo.tests.common import HttpCase, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.sale.tests.common import TestSaleCommon


@tagged("post_install", "-at_install")
class TestSaleTour(AccountTestInvoicingCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.agrolait = cls.env["res.partner"].create(
            {"name": "Agrolait", "email": "agro@lait.be"}
        )

    def test_01_sale_tour(self):
        self.env.ref("base.user_admin").write(
            {
                "email": "mitchell.admin@example.com",
            }
        )
        self.start_tour("/odoo", "sale_tour", login="admin")

    def test_04_portal_sale_signature_without_name_tour(self):
        self.agrolait.name = ""

        sales_order = (
            self.env["sale.order"]
            .sudo()
            .create(
                {
                    "name": "test SO",
                    "partner_id": self.agrolait.id,
                    "sent": True,
                    "require_payment": False,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                            }
                        )
                    ],
                }
            )
        )
        action = sales_order.action_preview_sale_order()

        self.start_tour(action["url"], "sale_signature_without_name", login="admin")


@tagged("-at_install", "post_install")
class TestSaleFlowTourPostInstall(TestSaleCommon, HttpCase):
    def test_basic_sale_flow_with_minimal_access_rights(self):
        sale_user = self.env["res.users"].create(
            {
                "name": "Super Sale Woman",
                "login": "SuperSaleWoman",
                "group_ids": [Command.set([self.ref("sale.group_sale_salesman")])],
            }
        )
        sale_order = (
            self.env["sale.order"]
            .with_user(sale_user.id)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "name": self.product.name,
                                "product_id": self.product.id,
                                "product_qty": 1,
                            }
                        )
                    ],
                }
            )
        )
        sale_order.action_confirm()
        self.start_tour(
            "/odoo",
            "test_basic_sale_flow_with_minimal_access_rights",
            login="SuperSaleWoman",
        )
