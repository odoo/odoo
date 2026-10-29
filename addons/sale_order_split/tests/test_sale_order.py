from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestSaleOrder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        """Setup the sale orders"""
        super().setUpClass()
        cls.partner1 = cls.env["res.partner"].create({"name": "Test partner 1"})
        cls.partner2 = cls.env["res.partner"].create({"name": "Test partner 2"})
        cls.category1 = cls.env["product.category"].create({"name": "Category 1"})
        cls.category2 = cls.env["product.category"].create({"name": "Category 2"})
        cls.category3 = cls.env["product.category"].create({"name": "Category 3"})
        cls.product1 = cls.env["product.product"].create(
            {"name": "Product 1", "categ_id": cls.category1.id}
        )
        cls.product2 = cls.env["product.product"].create(
            {"name": "Product 2", "categ_id": cls.category2.id}
        )
        cls.product3 = cls.env["product.product"].create(
            {"name": "Product 3", "categ_id": cls.category3.id}
        )

        cls.sale_order = cls.env["sale.order"].create(
            {
                "name": "S0001",
                "partner_id": cls.partner1.id,
                "order_line": [
                    (0, 0, {"product_id": cls.product1.id, "product_uom_qty": 2}),
                    (0, 0, {"product_id": cls.product2.id, "product_uom_qty": 3}),
                    (0, 0, {"product_id": cls.product3.id, "product_uom_qty": 4}),
                ],
            }
        )

    def test_action_split_sale_order_quotation(self):
        """Test cases to trigger the split sale order wizard"""
        action = self.sale_order.action_split_sale_order_quotation()
        self.assertEqual(action.get("name"), "Split Sale Order Wizard")
        self.assertEqual(action.get("type"), "ir.actions.act_window")
        self.assertEqual(action.get("res_model"), "sale.order.split.quotation")
        self.assertEqual(action.get("view_mode"), "form")
        self.assertEqual(action.get("target"), "new")

    def test_action_split_orders(self):
        """Test cases to open the view of split sale orders"""
        action = self.sale_order.action_split_orders()
        self.assertEqual(
            action["res_model"], "sale.order", "Invalid res_model in action"
        )
        self.assertEqual(
            action["view_mode"],
            "tree,kanban,form,calendar,pivot,graph,activity",
            "Invalid view_mode in action",
        )
        # Check the domain in the action
        expected_domain = [("split_sale_order_id", "=", self.sale_order.id)]
        self.assertEqual(action["domain"], expected_domain, "Invalid domain in action")

    def test_split_order_by_lines(self):
        """Test cases to Split order lines"""
        order_lines = self.sale_order.order_line.filtered(
            lambda line: line.product_id == self.product1
        )
        wizard = (
            self.env["sale.order.split.quotation"]
            .with_context(active_ids=self.sale_order.ids)
            .create({"split_sale_order_options": "order"})
        )
        wizard.action_apply()
        split_order = self.sale_order._split_order_by_lines(order_lines)
        self.assertTrue(split_order)
        self.assertEqual(split_order.split_sale_order_id, self.sale_order)
        self.assertEqual(len(split_order.order_line), 1)
        self.assertEqual(split_order.order_line[0].product_id, self.product1)

        # Splitting order lines for multiple products
        order_lines = self.sale_order.order_line.filtered(
            lambda line: line.product_id == self.product2
        )
        split_order = self.sale_order._split_order_by_lines(order_lines)
        self.assertTrue(split_order)
        self.assertEqual(split_order.split_sale_order_id, self.sale_order)
        self.assertEqual(len(split_order.order_line), 1)
        self.assertEqual(split_order.order_line[0].product_id, self.product2)

        # Attempting to split all order lines
        with self.assertRaises(UserError):
            self.sale_order._split_order_by_lines(self.sale_order.order_line)

    def test_split_order_by_category(self):
        """Test cases to Split order lines based on category"""
        self.sale_order._split_order_by_category()
        new_orders = self.env["sale.order"].search(
            [("split_sale_order_id", "=", self.sale_order.id)]
        )
        self.assertEqual(len(new_orders), 2)
        # Attempting to split an order with only one category
        sale_order = self.env["sale.order"].create(
            {
                "name": "S0002",
                "partner_id": self.partner2.id,
                "order_line": [
                    (0, 0, {"product_id": self.product1.id, "product_uom_qty": 2}),
                    (0, 0, {"product_id": self.product1.id, "product_uom_qty": 3}),
                ],
            }
        )
        with self.assertRaises(UserError):
            sale_order._split_order_by_category()

    def test_action_new_orders(self):
        # Create a single new split order
        wizard = self.env["sale.order.split.quotation"].create(
            {
                "split_sale_order_options": "order",
                "order_ids": [(4, self.sale_order.id)],
            }
        )
        new_order = self.env["sale.order"]
        action = wizard.action_new_orders(new_order)
        # Verify the action attributes
        self.assertEqual(action["res_model"], "sale.order")
