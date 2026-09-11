# Copyright 2014 Camptocamp SA (author: Guewen Baconnier)
# Copyright 2020 Camptocamp SA (author: Simone Orsi)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.user = cls.env["res.users"].create(
            {
                "name": "Sales Person",
                "login": "salesperson",
                "password": "salesperson",
                "groups_id": [
                    (4, cls.env.ref("sales_team.group_sale_manager").id),
                    (4, cls.env.ref("account.group_account_manager").id),
                ],
            }
        )
        cls.user.partner_id.email = "salesperson@example.com"


class TestAutomaticWorkflowMixin(object):
    def create_sale_order(self, workflow, override=None):
        sale_obj = self.env["sale.order"]

        partner_values = {
            "name": "Imperator Caius Julius Caesar Divus",
            "email": "test@example.com",
        }
        partner = self.env["res.partner"].create(partner_values)

        product_values = {"name": "Bread", "list_price": 5, "type": "product"}
        product = self.env["product.product"].create(product_values)
        self.product_uom_unit = self.env.ref("uom.product_uom_unit")
        values = {
            "partner_id": partner.id,
            "order_line": [
                (
                    0,
                    0,
                    {
                        "name": product.name,
                        "product_id": product.id,
                        "product_uom": self.product_uom_unit.id,
                        "price_unit": product.list_price,
                        "product_uom_qty": 1,
                    },
                )
            ],
            "workflow_process_id": workflow.id,
        }
        if override:
            values.update(override)
        order = sale_obj.create(values)
        # Create inventory
        for line in order.order_line:
            if line.product_id.type == "product":
                inventory = self.env["stock.quant"].create(
                    {
                        "product_id": line.product_id.id,
                        "location_id": self.env.ref("stock.stock_location_stock").id,
                        "inventory_quantity": line.product_uom_qty,
                    }
                )
                inventory._apply_inventory()
        return order

    def create_full_automatic(self, override=None):
        workflow_obj = self.env["sale.workflow.process"]
        values = workflow_obj.create(
            {
                "name": "Full Automatic",
                "picking_policy": "one",
                "validate_order": True,
                "validate_picking": True,
                "create_invoice": True,
                "validate_invoice": True,
                "send_invoice": True,
                "invoice_date_is_order_date": True,
            }
        )
        if override:
            values.update(override)
        return values

    def run_job(self):
        self.env["automatic.workflow.job"].run()
