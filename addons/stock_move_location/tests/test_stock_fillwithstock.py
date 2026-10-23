# Copyright Iryna Vyshnevska 2020 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import odoo.tests.common as common


class TestFillwithStock(common.TransactionCase):
    def setUp(self):
        super(TestFillwithStock, self).setUp()
        self.env = self.env(
            context=dict(
                self.env.context,
                tracking_disable=True,
            )
        )

        self.stock_location = self.env.ref("stock.stock_location_stock")
        self.pack_location = self.env.ref("stock.location_pack_zone")

        self.shelf1_location = self.env["stock.location"].create(
            {
                "name": "Test location",
                "usage": "internal",
                "location_id": self.stock_location.id,
            }
        )

        self.product1 = self.env["product.product"].create(
            {
                "name": "Product A",
                "type": "product",
            }
        )
        self.product2 = self.env["product.product"].create(
            {
                "name": "Product B",
                "type": "product",
            }
        )

        self.env["stock.quant"].create(
            {
                "product_id": self.product1.id,
                "location_id": self.shelf1_location.id,
                "quantity": 5.0,
                "reserved_quantity": 0.0,
            }
        )
        self.env["stock.quant"].create(
            {
                "product_id": self.product1.id,
                "location_id": self.shelf1_location.id,
                "quantity": 10.0,
                "reserved_quantity": 5.0,
            }
        )
        self.env["stock.quant"].create(
            {
                "product_id": self.product2.id,
                "location_id": self.shelf1_location.id,
                "quantity": 5.0,
                "reserved_quantity": 0.0,
            }
        )

    def test_fillwithstock(self):
        picking_stock_pack = self.env["stock.picking"].create(
            {
                "location_id": self.shelf1_location.id,
                "location_dest_id": self.pack_location.id,
                "picking_type_id": self.env.ref("stock.picking_type_internal").id,
            }
        )
        self.assertFalse(picking_stock_pack.move_ids)
        picking_stock_pack.button_fillwithstock()
        # picking filled with quants in bin
        self.assertEqual(len(picking_stock_pack.move_ids), 2)
        self.assertEqual(
            picking_stock_pack.move_ids.filtered(
                lambda m: m.product_id == self.product1
            ).product_uom_qty,
            10.0,
        )
        self.assertEqual(
            picking_stock_pack.move_ids.filtered(
                lambda m: m.product_id == self.product2
            ).product_uom_qty,
            5.0,
        )
