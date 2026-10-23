# Copyright 2015-2016 Akretion (http://www.akretion.com) - Alexis de Lattre
# Copyright 2016 ForgeFlow (http://www.forgeflow.com)
# Copyright 2016 Serpent Consulting Services (<http://www.serpentcs.com>)
# Copyright 2018 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestStockNoNegative(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_model = cls.env["product.product"]
        cls.product_ctg_model = cls.env["product.category"]
        cls.lot_model = cls.env["stock.lot"]
        cls.picking_type_id = cls.env.ref("stock.picking_type_out")
        cls.location_id = cls.env.ref("stock.stock_location_stock")
        cls.location_dest_id = cls.env.ref("stock.stock_location_customers")
        # Create product category
        cls.product_ctg = cls._create_product_category(cls)
        # Create a Product
        cls.product = cls._create_product(cls, "test_product1")
        # Create a Product With Lot
        cls.product_with_lot = cls._create_product_with_lot(cls, "test_lot_product1")
        # Create Lot
        cls.lot1 = cls._create_lot(cls, "lot1")
        cls._create_picking(cls)
        cls._create_picking_with_lot(cls)

    def _create_product_category(self):
        product_ctg = self.product_ctg_model.create(
            {"name": "test_product_ctg", "allow_negative_stock": False}
        )
        return product_ctg

    def _create_product(self, name):
        product = self.product_model.create(
            {
                "name": name,
                "categ_id": self.product_ctg.id,
                "type": "product",
                "allow_negative_stock": False,
            }
        )
        return product

    def _create_product_with_lot(self, name):
        product = self.product_model.create(
            {
                "name": name,
                "categ_id": self.product_ctg.id,
                "type": "product",
                "tracking": "lot",
                "allow_negative_stock": False,
            }
        )
        return product

    def _create_lot(self, name):
        lot = self.lot_model.create(
            {
                "name": name,
                "product_id": self.product_with_lot.id,
                "company_id": self.env.company.id,
            }
        )
        return lot

    def _create_picking(self):
        self.stock_picking = (
            self.env["stock.picking"]
            .with_context(test_stock_no_negative=True)
            .create(
                {
                    "picking_type_id": self.picking_type_id.id,
                    "move_type": "direct",
                    "location_id": self.location_id.id,
                    "location_dest_id": self.location_dest_id.id,
                }
            )
        )

        self.stock_move = self.env["stock.move"].create(
            {
                "name": "Test Move",
                "product_id": self.product.id,
                "product_uom_qty": 100.0,
                "product_uom": self.product.uom_id.id,
                "picking_id": self.stock_picking.id,
                "state": "draft",
                "location_id": self.location_id.id,
                "location_dest_id": self.location_dest_id.id,
                "quantity_done": 100.0,
            }
        )

    def _create_picking_with_lot(self):
        self.stock_picking_with_lot = (
            self.env["stock.picking"]
            .with_context(test_stock_no_negative=True)
            .create(
                {
                    "picking_type_id": self.picking_type_id.id,
                    "move_type": "direct",
                    "location_id": self.location_id.id,
                    "location_dest_id": self.location_dest_id.id,
                }
            )
        )

        self.stock_move_with_lot = self.env["stock.move"].create(
            {
                "name": "Test Move",
                "product_id": self.product_with_lot.id,
                "product_uom_qty": 100.0,
                "product_uom": self.product_with_lot.uom_id.id,
                "picking_id": self.stock_picking_with_lot.id,
                "state": "draft",
                "location_id": self.location_id.id,
                "location_dest_id": self.location_dest_id.id,
            }
        )

    def test_check_constrains(self):
        """Assert that constraint is raised when user
        tries to validate the stock operation which would
        make the stock level of the product negative"""
        self.stock_picking.action_confirm()
        with self.assertRaises(ValidationError):
            self.stock_picking.button_validate()

    def test_true_allow_negative_stock_product(self):
        """Assert that negative stock levels are allowed when
        the allow_negative_stock is set active in the product"""
        self.product.allow_negative_stock = True
        self.stock_picking.action_confirm()
        self.stock_picking.button_validate()
        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product.id),
                ("location_id", "=", self.location_id.id),
            ]
        )
        self.assertEqual(quant.quantity, -100)

    def test_true_allow_negative_stock_location(self):
        """Assert that negative stock levels are allowed when
        the allow_negative_stock is set active in the product"""
        self.product.allow_negative_stock = False
        self.location_id.allow_negative_stock = True
        self.stock_picking.action_confirm()
        self.stock_picking.button_validate()
        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product.id),
                ("location_id", "=", self.location_id.id),
            ]
        )
        self.assertEqual(quant.quantity, -100)

    def test_true_allow_negative_stock_product_with_lot(self):
        """Assert that negative stock levels are allowed when
        the allow_negative_stock is set active in the product with lot"""
        self.product_with_lot.allow_negative_stock = True
        self.stock_picking_with_lot.action_confirm()
        self.stock_picking_with_lot.move_ids.quantity_done = 100
        with self.assertRaises(UserError):
            self.stock_picking_with_lot._action_done()
        self.stock_picking_with_lot.move_ids.move_line_ids[0].lot_id = self.lot1.id
        self.stock_picking_with_lot._action_done()
        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_with_lot.id),
                ("location_id", "=", self.location_id.id),
                ("lot_id", "=", self.lot1.id),
            ]
        )
        self.assertEqual(quant.quantity, -100)
