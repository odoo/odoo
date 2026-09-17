from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form
from odoo.tests.common import new_test_user

from odoo.addons.stock.tests.common import TestStockCommon


class TestWarehouse(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Acme Corporation"})

    def test_inventory_product(self):
        self.product_1.is_storable = True
        product_1_quant = (
            self.env["stock.quant"]
            .with_context(inventory_mode=True)
            .create(
                {
                    "product_id": self.product_1.id,
                    "inventory_quantity": 50.0,
                    "location_id": self.warehouse_1.lot_stock_id.id,
                }
            )
        )
        product_1_quant.action_apply_inventory()

        move_in_id = self.env["stock.move"].search(
            [("is_inventory", "=", True), ("product_id", "=", self.product_1.id)]
        )
        self.assertEqual(len(move_in_id), 1)
        self.assertEqual(move_in_id.product_qty, 50.0)
        self.assertEqual(product_1_quant.quantity, 50.0)
        self.assertEqual(move_in_id.product_uom_id, self.product_1.uom_id)
        self.assertEqual(move_in_id.state, "done")

        product_1_quant.inventory_quantity = 35.0
        product_1_quant.action_apply_inventory()

        move_ids = self.env["stock.move"].search(
            [("is_inventory", "=", True), ("product_id", "=", self.product_1.id)]
        )
        self.assertEqual(len(move_ids), 2)
        move_out_id = move_ids[-1]
        self.assertEqual(move_out_id.product_qty, 15.0)
        self.assertEqual(move_out_id.location_id, self.warehouse_1.lot_stock_id)
        self.assertEqual(
            move_out_id.location_dest_id, self.product_1.property_stock_inventory
        )
        self.assertEqual(move_out_id.state, "done")

        quants = self.env["stock.quant"]._gather(
            self.product_1, self.product_1.property_stock_inventory
        )
        self.assertEqual(len(quants), 1)

        self.assertEqual(
            self.env["stock.quant"]
            ._gather(self.product_1, self.warehouse_1.lot_stock_id)
            .quantity,
            35.0,
        )
        self.assertEqual(
            self.env["stock.quant"]
            ._gather(self.product_1, self.warehouse_1.lot_stock_id.location_id)
            .quantity,
            35.0,
        )
        self.assertEqual(
            self.env["stock.quant"]
            ._gather(self.product_1, self.warehouse_1.view_location_id)
            .quantity,
            35.0,
        )

        self.assertEqual(
            self.env["stock.quant"]
            ._gather(self.product_1, self.warehouse_1.wh_input_stock_loc_id)
            .quantity,
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]
            ._gather(self.product_1, self.env.ref("stock.stock_location_stock"))
            .quantity,
            0.0,
        )

    def test_initial_quant_location(self):
        warehouse = self.env["stock.warehouse"].create(
            {
                "name": "Mixed locations",
                "code": "TEST",
                "sequence": 0,
            }
        )
        warehouse.in_type_id.default_location_dest_id = self.supplier_location

        quant = self.env["stock.quant"].new(
            {
                "product_id": self.product_1.id,
                "inventory_quantity": 1,
            }
        )
        quant._onchange_product_id()

        self.assertEqual(
            quant.location_id,
            warehouse.lot_stock_id,
            "a new quant defaults to the stock of the first warehouse, not to "
            "wherever its receipts happen to be aimed",
        )

    def test_basic_move(self):
        self.user_stock_manager.group_ids += self.env.ref(
            "product.group_product_manager"
        )
        product = self.product_3.with_user(self.user_stock_manager)
        product.is_storable = True
        picking_out = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.warehouse_1.lot_stock_id.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        customer_move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": 5,
                "product_uom_id": product.uom_id.id,
                "picking_id": picking_out.id,
                "location_id": self.warehouse_1.lot_stock_id.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        self.assertEqual(customer_move.product_uom_id, product.uom_id)
        self.assertEqual(customer_move.location_id, self.warehouse_1.lot_stock_id)
        self.assertEqual(customer_move.location_dest_id, self.customer_location)

        customer_move._action_confirm()
        self.assertEqual(product.qty_available, 0.0)
        self.assertEqual(product.qty_available_virtual, -5.0)

        customer_move.quantity = 5
        customer_move.picked = True
        customer_move._action_done()
        self.assertEqual(product.qty_available, -5.0)

        receive_move = self._create_move(
            product,
            self.supplier_location,
            self.warehouse_1.lot_stock_id,
            product_uom_qty=15,
        )

        receive_move._action_confirm()
        receive_move.quantity = 15
        receive_move.picked = True
        receive_move._action_done()

        product._compute_quantities()
        self.assertEqual(product.qty_available, 10.0)
        self.assertEqual(product.qty_available_virtual, 10.0)

        customer_move_2 = self._create_move(
            product,
            self.warehouse_1.lot_stock_id,
            self.customer_location,
            product_uom_qty=2,
        )

        customer_move_2._action_confirm()
        product._compute_quantities()
        self.assertEqual(product.qty_available, 10.0)
        self.assertEqual(product.qty_available_virtual, 8.0)

        customer_move_2.quantity = 2.0
        customer_move_2.picked = True
        customer_move_2._action_done()
        product._compute_quantities()
        self.assertEqual(product.qty_available, 8.0)

    def test_inventory_adjustment_and_negative_quants_1(self):
        productA = self.env["product.product"].create(
            {"name": "Product A", "is_storable": True}
        )

        picking_out = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        self.env["stock.move"].create(
            {
                "product_id": productA.id,
                "product_uom_qty": 1,
                "product_uom_id": productA.uom_id.id,
                "picking_id": picking_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        picking_out.action_confirm()
        picking_out.move_ids.quantity = 1
        picking_out.move_ids.picked = True
        picking_out._action_done()

        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", productA.id),
                ("location_id", "=", self.stock_location.id),
            ]
        )
        self.assertEqual(len(quant), 1)
        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=picking_out.ids,
                active_id=picking_out.ids[0],
                active_model="stock.picking",
            )
        )
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env["stock.picking"].browse(
            stock_return_picking_action["res_id"]
        )
        return_pick.action_assign()
        return_pick.move_ids.quantity = 1
        return_pick.move_ids.picked = True
        return_pick._action_done()

        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", productA.id),
                ("location_id", "=", self.stock_location.id),
            ]
        )
        self.assertEqual(sum(quant.mapped("quantity")), 0)

    def test_inventory_adjustment_and_negative_quants_2(self):
        productA = self.env["product.product"].create(
            {"name": "Product A", "is_storable": True}
        )
        location_loss = productA.property_stock_inventory

        picking_out = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        self.env["stock.move"].create(
            {
                "product_id": productA.id,
                "product_uom_qty": 1,
                "product_uom_id": productA.uom_id.id,
                "picking_id": picking_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        picking_out.action_confirm()
        picking_out.move_ids.quantity = 1
        picking_out.move_ids.picked = True
        picking_out._action_done()

        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", productA.id),
                ("location_id", "=", self.stock_location.id),
            ]
        )
        self.assertEqual(len(quant), 1, "Wrong number of quants created.")
        self.assertEqual(quant.quantity, -1, "Theoretical quantity should be -1.")
        quant.inventory_quantity = 0
        quant.action_apply_inventory()

        move = self.env["stock.move"].search(
            [("product_id", "=", productA.id), ("is_inventory", "=", True)]
        )
        self.assertEqual(len(move), 1)
        self.assertEqual(move.product_qty, 1, "Moves created with wrong quantity.")
        self.assertEqual(move.location_id.id, location_loss.id)

        self.env["stock.quant"]._run_maintenance_tasks()
        quants = self.env["stock.quant"].search(
            [
                ("product_id", "=", productA.id),
                ("location_id", "=", self.stock_location.id),
            ]
        )
        self.assertEqual(sum(quants.mapped("quantity")), 0)

        quant = self.env["stock.quant"].search(
            [("product_id", "=", productA.id), ("location_id", "=", location_loss.id)]
        )
        self.assertEqual(len(quant), 1)

    def test_resupply_route(self):
        warehouse_stock = self.env["stock.warehouse"].create(
            {
                "name": "Stock.",
                "code": "STK",
            }
        )

        distribution_partner = self.env["res.partner"].create(
            {"name": "Distribution Center"}
        )
        warehouse_distribution = self.env["stock.warehouse"].create(
            {
                "name": "Dist.",
                "code": "DIST",
                "resupply_wh_ids": [Command.set([warehouse_stock.id])],
                "partner_id": distribution_partner.id,
            }
        )

        warehouse_shop = self.env["stock.warehouse"].create(
            {
                "name": "Shop",
                "code": "SHOP",
                "resupply_wh_ids": [Command.set([warehouse_distribution.id])],
            }
        )

        route_stock_to_dist = warehouse_distribution.resupply_route_ids
        route_dist_to_shop = warehouse_shop.resupply_route_ids

        route_dist_to_shop.rule_ids.procure_method = "make_to_order"

        product = self.env["product.product"].create(
            {
                "name": "Fakir",
                "is_storable": True,
                "route_ids": [
                    Command.link(route_id)
                    for route_id in [
                        route_stock_to_dist.id,
                        route_dist_to_shop.id,
                        self.warehouse_1.mto_pull_id.route_id.id,
                    ]
                ],
            }
        )

        picking_out = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.picking_type_out.id,
                "location_id": warehouse_shop.lot_stock_id.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": 1,
                "product_uom_id": product.uom_id.id,
                "picking_id": picking_out.id,
                "location_id": warehouse_shop.lot_stock_id.id,
                "location_dest_id": self.customer_location.id,
                "warehouse_id": warehouse_shop.id,
                "procure_method": "make_to_order",
            }
        )
        picking_out.action_confirm()

        moves = self.env["stock.move"].search([("product_id", "=", product.id)])
        self.assertEqual(len(moves), 5, "Invalid moves number.")
        self.assertTrue(
            self.env["stock.move"].search(
                [("location_id", "=", warehouse_stock.lot_stock_id.id)]
            )
        )
        self.assertTrue(
            self.env["stock.move"].search(
                [("location_dest_id", "=", warehouse_distribution.lot_stock_id.id)]
            )
        )
        self.assertTrue(
            self.env["stock.move"].search(
                [("location_id", "=", warehouse_distribution.lot_stock_id.id)]
            )
        )
        self.assertTrue(
            self.env["stock.move"].search(
                [("location_dest_id", "=", warehouse_shop.lot_stock_id.id)]
            )
        )
        self.assertTrue(
            self.env["stock.move"].search(
                [("location_id", "=", warehouse_shop.lot_stock_id.id)]
            )
        )

        self.assertTrue(
            self.env["stock.picking"].search(
                [
                    (
                        "location_id",
                        "=",
                        self.env.company.internal_transit_location_id.id,
                    ),
                    ("partner_id", "=", distribution_partner.id),
                ]
            )
        )
        self.assertTrue(
            self.env["stock.picking"].search(
                [
                    (
                        "location_dest_id",
                        "=",
                        self.env.company.internal_transit_location_id.id,
                    ),
                    ("partner_id", "=", distribution_partner.id),
                ]
            )
        )

    def test_mutiple_resupply_warehouse(self):
        customer_location = self.customer_location

        warehouse_distribution_wavre = self.env["stock.warehouse"].create(
            {
                "name": "Stock Wavre.",
                "code": "WV",
            }
        )

        warehouse_shop_wavre = self.env["stock.warehouse"].create(
            {
                "name": "Shop Wavre",
                "code": "SHWV",
                "resupply_wh_ids": [Command.set([warehouse_distribution_wavre.id])],
            }
        )

        warehouse_distribution_namur = self.env["stock.warehouse"].create(
            {
                "name": "Stock Namur.",
                "code": "NM",
            }
        )

        warehouse_shop_namur = self.env["stock.warehouse"].create(
            {
                "name": "Shop Namur",
                "code": "SHNM",
                "resupply_wh_ids": [Command.set([warehouse_distribution_namur.id])],
            }
        )

        route_shop_namur = warehouse_shop_namur.resupply_route_ids
        route_shop_wavre = warehouse_shop_wavre.resupply_route_ids
        product = self.env["product.product"].create(
            {
                "name": "Fakir",
                "is_storable": True,
                "route_ids": [
                    Command.link(route_id)
                    for route_id in [
                        route_shop_namur.id,
                        route_shop_wavre.id,
                        self.warehouse_1.mto_pull_id.route_id.id,
                    ]
                ],
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            product, warehouse_distribution_wavre.lot_stock_id, 1.0
        )
        self.env["stock.quant"]._update_available_quantity(
            product, warehouse_distribution_namur.lot_stock_id, 1.0
        )

        picking_out_namur = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.picking_type_out.id,
                "location_id": warehouse_shop_namur.lot_stock_id.id,
                "location_dest_id": customer_location.id,
                "state": "draft",
            }
        )
        self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": 1,
                "product_uom_id": product.uom_id.id,
                "picking_id": picking_out_namur.id,
                "location_id": warehouse_shop_namur.lot_stock_id.id,
                "location_dest_id": customer_location.id,
                "warehouse_id": warehouse_shop_namur.id,
                "procure_method": "make_to_order",
            }
        )
        picking_out_namur.action_confirm()

        picking_stock_transit = self.env["stock.picking"].search(
            [("location_id", "=", warehouse_distribution_namur.lot_stock_id.id)]
        )
        self.assertTrue(picking_stock_transit)
        picking_stock_transit.action_assign()
        picking_stock_transit.move_ids[0].quantity = 1.0
        picking_stock_transit.move_ids[0].picked = True
        picking_stock_transit._action_done()

        picking_transit_shop_namur = self.env["stock.picking"].search(
            [("location_dest_id", "=", warehouse_shop_namur.lot_stock_id.id)]
        )
        self.assertTrue(picking_transit_shop_namur)
        picking_transit_shop_namur.action_assign()
        picking_transit_shop_namur.move_ids[0].quantity = 1.0
        picking_transit_shop_namur.move_ids[0].picked = True
        picking_transit_shop_namur._action_done()

        picking_out_namur.action_assign()
        picking_out_namur.move_ids[0].picked = True
        picking_out_namur.move_ids[0].quantity = 1.0
        picking_out_namur._action_done()

        self.assertEqual(
            self.env["stock.quant"]._gather(product, customer_location).quantity, 1
        )
        self.assertEqual(
            sum(
                self.env["stock.quant"]
                ._gather(product, warehouse_distribution_namur.lot_stock_id)
                .mapped("quantity")
            ),
            0,
        )

        picking_out_wavre = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.picking_type_out.id,
                "location_id": warehouse_shop_wavre.lot_stock_id.id,
                "location_dest_id": customer_location.id,
                "state": "draft",
            }
        )
        self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": 1,
                "product_uom_id": product.uom_id.id,
                "picking_id": picking_out_wavre.id,
                "location_id": warehouse_shop_wavre.lot_stock_id.id,
                "location_dest_id": customer_location.id,
                "warehouse_id": warehouse_shop_wavre.id,
                "procure_method": "make_to_order",
            }
        )
        picking_out_wavre.action_confirm()

        picking_stock_transit = self.env["stock.picking"].search(
            [("location_id", "=", warehouse_distribution_wavre.lot_stock_id.id)]
        )
        self.assertTrue(picking_stock_transit)
        picking_stock_transit.action_assign()
        picking_stock_transit.move_ids[0].quantity = 1.0
        picking_stock_transit.move_ids[0].picked = True
        picking_stock_transit._action_done()

        picking_transit_shop_wavre = self.env["stock.picking"].search(
            [("location_dest_id", "=", warehouse_shop_wavre.lot_stock_id.id)]
        )
        self.assertTrue(picking_transit_shop_wavre)
        picking_transit_shop_wavre.action_assign()
        picking_transit_shop_wavre.move_ids[0].quantity = 1.0
        picking_transit_shop_wavre.move_ids[0].picked = True
        picking_transit_shop_wavre._action_done()

        picking_out_wavre.action_assign()
        picking_out_wavre.move_ids[0].quantity = 1.0
        picking_out_wavre.move_ids[0].picked = True
        picking_out_wavre._action_done()

        self.assertEqual(
            self.env["stock.quant"]._gather(product, customer_location).quantity, 2
        )
        self.assertEqual(
            sum(
                self.env["stock.quant"]
                ._gather(product, warehouse_distribution_wavre.lot_stock_id)
                .mapped("quantity")
            ),
            0,
        )

    def test_add_resupply_warehouse_one_by_one(self):
        warehouse_A, warehouse_B, warehouse_C = self.env["stock.warehouse"].create(
            [
                {
                    "name": code,
                    "code": code,
                }
                for code in ["WH_A", "WH_B", "WH_C"]
            ]
        )
        warehouse_A.resupply_wh_ids = [Command.link(warehouse_B.id)]
        self.assertEqual(len(warehouse_A.resupply_route_ids), 1)
        self.assertEqual(warehouse_A.resupply_route_ids.supplier_wh_id, warehouse_B)
        warehouse_A.resupply_wh_ids = [Command.link(warehouse_C.id)]
        self.assertEqual(len(warehouse_A.resupply_route_ids), 2)
        self.assertRecordValues(
            warehouse_A.resupply_route_ids.sorted("id"),
            [
                {"supplier_wh_id": warehouse_B.id},
                {"supplier_wh_id": warehouse_C.id},
            ],
        )

    def test_toggle_resupply_warehouse(self):
        warehouse_A = self.env["stock.warehouse"].create(
            {
                "name": "Warehouse A",
                "code": "WH_A",
            }
        )
        warehouse_B = self.env["stock.warehouse"].create(
            {
                "name": "Warehouse B",
                "code": "WH_B",
                "resupply_wh_ids": [Command.set(warehouse_A.ids)],
            }
        )
        resupply_route = warehouse_B.resupply_route_ids
        self.assertTrue(resupply_route.active, "Route should be active")
        warehouse_B.resupply_wh_ids = [Command.set([])]
        self.assertFalse(warehouse_B.resupply_route_ids)
        self.assertFalse(resupply_route.active, "Route should now be inactive")
        warehouse_B.resupply_wh_ids = [Command.set(warehouse_A.ids)]
        self.assertEqual(warehouse_B.resupply_route_ids, resupply_route)
        self.assertTrue(resupply_route.active, "Route should now be active")

    def test_muti_step_resupply_warehouse(self):
        warehouse_A = self.env["stock.warehouse"].create(
            {
                "name": "Warehouse A",
                "code": "WH_A",
                "delivery_steps": "pick_pack_ship",
            }
        )
        warehouse_B = self.env["stock.warehouse"].create(
            {
                "name": "Warehouse B",
                "code": "WH_B",
                "reception_steps": "three_steps",
                "resupply_wh_ids": [Command.link(warehouse_A.id)],
            }
        )
        self.product_3.write(
            {
                "type": "consu",
                "is_storable": True,
                "route_ids": [Command.link(warehouse_B.resupply_route_ids.id)],
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_3, warehouse_A.lot_stock_id, 1.0
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_3, warehouse_A.lot_stock_id
            ),
            1,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_3, warehouse_B.lot_stock_id
            ),
            0,
        )

        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "location_id": warehouse_B.lot_stock_id.id,
                "product_id": self.product_3.id,
                "qty_to_order": 1.0,
            }
        )
        orderpoint.action_replenish()
        move = self.env["stock.move"].search(
            [
                ("location_id", "=", warehouse_A.lot_stock_id.id),
                ("origin", "=", orderpoint.name),
            ]
        )
        self.assertTrue(move, "No move created from WH_A/Stock")

        inter_wh_loc = self.env.company.internal_transit_location_id
        step_location_ids = [
            (
                warehouse_A.lot_stock_id.id,
                warehouse_A.wh_pack_stock_loc_id.id,
            ),
            (
                warehouse_A.wh_pack_stock_loc_id.id,
                warehouse_A.wh_output_stock_loc_id.id,
            ),
            (
                warehouse_A.wh_output_stock_loc_id.id,
                inter_wh_loc.id,
            ),
            (
                inter_wh_loc.id,
                warehouse_B.wh_input_stock_loc_id.id,
            ),
            (
                warehouse_B.wh_input_stock_loc_id.id,
                warehouse_B.wh_qc_stock_loc_id.id,
            ),
            (
                warehouse_B.wh_qc_stock_loc_id.id,
                warehouse_B.lot_stock_id.id,
            ),
        ]
        for loc_src_id, loc_dest_id in step_location_ids:
            self.assertEqual(move.location_id.id, loc_src_id)
            self.assertEqual(move.location_dest_id.id, loc_dest_id)
            move.picked = True
            move._action_done()
            self.assertEqual(move.state, "done")
            move = move.move_dest_ids
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_3, warehouse_A.lot_stock_id
            ),
            0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product_3, warehouse_B.lot_stock_id
            ),
            1,
        )

    def test_change_delivery_step_resupply_warehouse(self):
        warehouse_A = self.env["stock.warehouse"].create(
            {
                "name": "Warehouse X",
                "code": "WH_X",
            }
        )
        warehouse_B = self.env["stock.warehouse"].create(
            {
                "name": "Warehouse Y",
                "code": "WH_Y",
                "resupply_wh_ids": [Command.link(warehouse_A.id)],
            }
        )
        resupply_rules = warehouse_B.resupply_route_ids.rule_ids
        self.assertEqual(len(resupply_rules), 2)
        stock_A_to_transit = resupply_rules.filtered(
            lambda r: (
                r.location_dest_id == self.env.company.internal_transit_location_id
            )
        )
        self.assertEqual(stock_A_to_transit.location_src_id, warehouse_A.lot_stock_id)

        warehouse_A.delivery_steps = "pick_pack_ship"
        new_resupply_rules = warehouse_B.resupply_route_ids.rule_ids
        self.assertEqual(len(new_resupply_rules), 3)
        self.assertEqual(
            stock_A_to_transit.location_src_id, warehouse_A.wh_output_stock_loc_id
        )
        stock_to_output = new_resupply_rules - resupply_rules
        self.assertEqual(stock_to_output.location_src_id, warehouse_A.lot_stock_id)
        self.assertEqual(
            stock_to_output.location_dest_id, warehouse_A.wh_output_stock_loc_id
        )

        warehouse_A.delivery_steps = "pick_ship"
        self.assertEqual(warehouse_B.resupply_route_ids.rule_ids, new_resupply_rules)
        self.assertEqual(
            stock_A_to_transit.location_src_id, warehouse_A.wh_output_stock_loc_id
        )
        self.assertEqual(
            stock_to_output.location_dest_id, warehouse_A.wh_output_stock_loc_id
        )

        warehouse_A.delivery_steps = "ship_only"
        self.assertEqual(warehouse_B.resupply_route_ids.rule_ids, resupply_rules)
        self.assertEqual(stock_A_to_transit.location_src_id, warehouse_A.lot_stock_id)
        self.assertFalse(
            stock_to_output.active, "The intermediate rule should have been archived."
        )

        warehouse_A.delivery_steps = "pick_ship"
        self.assertTrue(
            stock_to_output.active, "The intermediate rule should have been unarchived."
        )
        self.assertEqual(
            warehouse_B.resupply_route_ids.rule_ids,
            new_resupply_rules,
            "No new rule should have been created.",
        )

    def test_noleak(self):
        partner = self.env["res.partner"].create({"name": "Chicago partner"})
        company = self.env["res.company"].create(
            {"name": "My Company (Chicago)1", "currency_id": self.ref("base.USD")}
        )
        self.env["stock.warehouse"].create(
            {
                "name": "Chicago Warehouse2",
                "company_id": company.id,
                "code": "Chic2",
                "partner_id": partner.id,
            }
        )
        wh = self.env["stock.warehouse"].search([])

        assert len(set(wh.mapped("company_id.id"))) > 1

        companies_before = wh.mapped(lambda w: (w.id, w.company_id))
        wh.name = "whatever"
        companies_after = wh.mapped(lambda w: (w.id, w.company_id))

        self.assertEqual(companies_after, companies_before)

    def test_toggle_active_warehouse_1(self):
        wh = Form(self.env["stock.warehouse"])
        wh.name = "The attic of Willy"
        wh.code = "WIL"
        warehouse = wh.save()

        custom_location = Form(self.env["stock.location"])
        custom_location.name = "A Trunk"
        custom_location.location_id = warehouse.lot_stock_id
        custom_location = custom_location.save()

        warehouse.action_archive()
        self.assertFalse(warehouse.mto_pull_id.active)

        self.assertFalse(warehouse.reception_route_id.active)
        self.assertFalse(warehouse.delivery_route_id.active)

        self.assertFalse(warehouse.lot_stock_id.active)
        self.assertFalse(warehouse.wh_input_stock_loc_id.active)
        self.assertFalse(warehouse.wh_qc_stock_loc_id.active)
        self.assertFalse(warehouse.wh_output_stock_loc_id.active)
        self.assertFalse(warehouse.wh_pack_stock_loc_id.active)
        self.assertFalse(custom_location.active)

        self.assertFalse(warehouse.in_type_id.active)
        self.assertFalse(warehouse.out_type_id.active)
        self.assertFalse(warehouse.int_type_id.active)
        self.assertFalse(warehouse.pick_type_id.active)
        self.assertFalse(warehouse.pack_type_id.active)

        warehouse.action_unarchive()
        self.assertTrue(warehouse.mto_pull_id.active)

        self.assertTrue(warehouse.reception_route_id.active)
        self.assertTrue(warehouse.delivery_route_id.active)

        self.assertTrue(warehouse.lot_stock_id.active)
        self.assertFalse(warehouse.wh_input_stock_loc_id.active)
        self.assertFalse(warehouse.wh_qc_stock_loc_id.active)
        self.assertFalse(warehouse.wh_output_stock_loc_id.active)
        self.assertFalse(warehouse.wh_pack_stock_loc_id.active)
        self.assertTrue(custom_location.active)

        self.assertTrue(warehouse.in_type_id.active)
        self.assertTrue(warehouse.out_type_id.active)
        self.assertTrue(warehouse.int_type_id.active)
        self.assertFalse(warehouse.pick_type_id.active)
        self.assertFalse(warehouse.pack_type_id.active)

    def test_toggle_active_blocked_by_foreign_picking_type(self):
        Warehouse = self.env["stock.warehouse"]
        wh_a = Warehouse.create({"name": "Archive Me", "code": "ARM"})
        wh_b = Warehouse.create({"name": "Other WH", "code": "OTH"})
        customer_loc = self.env.ref("stock.stock_location_customers")

        self.env["stock.picking.type"].create(
            {
                "name": "Foreign src-only",
                "code": "outgoing",
                "sequence_code": "FSO",
                "warehouse_id": wh_b.id,
                "default_location_src_id": wh_a.lot_stock_id.id,
                "default_location_dest_id": customer_loc.id,
                "company_id": wh_a.company_id.id,
            }
        )

        with self.assertRaises(UserError):
            wh_a.action_archive()
        self.assertTrue(
            wh_a.lot_stock_id.active,
            "The stock location must stay active since archiving was refused.",
        )

    def test_toggle_active_warehouse_2(self):
        self.env.user.group_ids += self.env.ref("stock.group_adv_location")
        wh = Form(self.env["stock.warehouse"])
        wh.name = "The attic of Willy"
        wh.code = "WIL"
        wh.reception_steps = "two_steps"
        wh.delivery_steps = "pick_pack_ship"
        warehouse = wh.save()

        warehouse.resupply_wh_ids = [Command.set([self.warehouse_1.id])]

        custom_location = Form(self.env["stock.location"])
        custom_location.name = "A Trunk"
        custom_location.location_id = warehouse.lot_stock_id
        custom_location = custom_location.save()

        warehouse.reception_route_id.warehouse_ids = [Command.link(self.warehouse_1.id)]

        route = Form(self.env["stock.route"])
        route.name = "Stair"
        route = route.save()

        route.warehouse_ids = [Command.set([warehouse.id, self.warehouse_1.id])]

        warehouse.delivery_route_id.action_archive()
        warehouse.wh_pack_stock_loc_id.action_archive()

        warehouse.action_archive()
        self.assertFalse(warehouse.mto_pull_id.active)

        self.assertTrue(warehouse.reception_route_id.active)
        self.assertFalse(warehouse.delivery_route_id.active)
        self.assertTrue(route.active)

        self.assertFalse(warehouse.lot_stock_id.active)
        self.assertFalse(warehouse.wh_input_stock_loc_id.active)
        self.assertFalse(warehouse.wh_qc_stock_loc_id.active)
        self.assertFalse(warehouse.wh_output_stock_loc_id.active)
        self.assertFalse(warehouse.wh_pack_stock_loc_id.active)
        self.assertFalse(custom_location.active)

        self.assertFalse(warehouse.in_type_id.active)
        self.assertFalse(warehouse.out_type_id.active)
        self.assertFalse(warehouse.int_type_id.active)
        self.assertFalse(warehouse.pick_type_id.active)
        self.assertFalse(warehouse.pack_type_id.active)

        warehouse.action_unarchive()
        self.assertTrue(warehouse.mto_pull_id.active)

        self.assertTrue(warehouse.reception_route_id.active)
        self.assertTrue(warehouse.delivery_route_id.active)

        self.assertTrue(warehouse.lot_stock_id.active)
        self.assertTrue(warehouse.wh_input_stock_loc_id.active)
        self.assertFalse(warehouse.wh_qc_stock_loc_id.active)
        self.assertTrue(warehouse.wh_output_stock_loc_id.active)
        self.assertTrue(warehouse.wh_pack_stock_loc_id.active)
        self.assertTrue(custom_location.active)

        self.assertTrue(warehouse.in_type_id.active)
        self.assertTrue(warehouse.out_type_id.active)
        self.assertTrue(warehouse.int_type_id.active)
        self.assertTrue(warehouse.pick_type_id.active)
        self.assertTrue(warehouse.pack_type_id.active)

    def test_edit_warehouse_1(self):
        wh = Form(self.env["stock.warehouse"])
        wh.name = "Chicago"
        wh.code = "chic"
        warehouse = wh.save()
        self.assertEqual(warehouse.code, "CHIC")
        self.assertEqual(warehouse.int_type_id.barcode, "CHICINT")
        self.assertEqual(warehouse.int_type_id.sequence_id.prefix, "CHIC/INT/")

        wh = Form(warehouse)
        wh.code = "CH"
        wh.save()
        self.assertEqual(warehouse.int_type_id.barcode, "CHINT")
        self.assertEqual(warehouse.int_type_id.sequence_id.prefix, "CH/INT/")

    def test_warehouse_code_is_stored_canonical(self):
        first = self.env["stock.warehouse"].create({"name": "Spaced", "code": "wh a"})
        self.assertEqual(first.code, "WHA")
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.env["stock.warehouse"].create({"name": "Tight", "code": "WHA"})

    def test_create_warehouse_without_company_defaults(self):
        Warehouse = self.env["stock.warehouse"]
        wh = Warehouse.create({"name": "No Company WH"})
        self.assertTrue(wh.code, "a short name should be auto-generated")
        self.assertEqual(wh.company_id, self.env.company)
        self.assertTrue(wh.view_location_id.name, "the view location must be named")
        self.assertEqual(wh.view_location_id.company_id, self.env.company)
        wh2 = Warehouse.create({})
        self.assertTrue(wh2.code)
        self.assertTrue(wh2.name)

    def test_multiwarehouse_group_implied_on_warehouse_creation(self):
        group_user = self.env.ref("base.group_user")
        group_multi_wh = self.env.ref("stock.group_stock_multi_warehouses")
        group_multi_loc = self.env.ref("stock.group_stock_multi_locations")
        Warehouse = self.env["stock.warehouse"]

        company = self.env["res.company"].create({"name": "Multi-WH Co"})
        Warehouse.create({"name": "MW A", "code": "MWA", "company_id": company.id})

        group_user.write({"implied_ids": [(3, group_multi_wh.id)]})
        self.assertNotIn(group_multi_wh, group_user.implied_ids)

        Warehouse.create({"name": "MW B", "code": "MWB", "company_id": company.id})
        self.assertIn(
            group_multi_wh,
            group_user.implied_ids,
            "a company with several active warehouses must imply the "
            "multi-warehouse group",
        )
        self.assertIn(
            group_multi_loc,
            group_user.implied_ids,
            "the multi-warehouse group must pull in the multi-locations group",
        )

    def test_location_warehouse(self):
        wh = self.env["stock.warehouse"].create(
            {
                "name": "Main Test Warehouse",
                "code": "MTWH",
            }
        )
        test_warehouse = self.warehouse_1
        location = test_warehouse.lot_stock_id
        self.assertEqual(location.warehouse_id, test_warehouse)

        test_warehouse.view_location_id.location_id = wh.lot_stock_id.id
        wh.sequence = 100
        test_warehouse.sequence = 1
        location._compute_warehouse_id()
        self.assertEqual(location.warehouse_id, test_warehouse)

        wh.sequence = 1
        test_warehouse.sequence = 100
        location._compute_warehouse_id()
        self.assertEqual(location.warehouse_id, test_warehouse)

    def test_location_updates_wh(self):
        warehouse_A = self.env["stock.warehouse"].create(
            {"name": "Warehouse X", "code": "WH_X", "delivery_steps": "pick_pack_ship"}
        )
        warehouse_B = self.env["stock.warehouse"].create(
            {"name": "Warehouse Y", "code": "WH_Y", "delivery_steps": "pick_pack_ship"}
        )
        picking_out = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": warehouse_A.pick_type_id.id,
                "location_id": warehouse_A.lot_stock_id.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        customer_move = self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 1,
                "product_uom_id": self.product.uom_id.id,
                "picking_id": picking_out.id,
                "location_id": warehouse_A.lot_stock_id.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        picking_form = Form(picking_out)
        picking_form.picking_type_id = warehouse_B.pick_type_id
        picking_form.save()
        self.assertEqual(customer_move.warehouse_id, warehouse_B)
        self.assertEqual(picking_out.picking_type_id, warehouse_B.pick_type_id)
        picking_out.button_validate()
        self.assertEqual(customer_move.move_dest_ids.warehouse_id, warehouse_B)

    def test_multi_step_routes_multi_company(self):
        companies = self.env["res.company"].create(
            [
                {"name": "COMP1"},
                {"name": "COMP2"},
            ]
        )
        warehouses = self.env["stock.warehouse"].create(
            [
                {
                    "name": "Warehouse 1",
                    "company_id": companies.ids[0],
                    "code": "WHC1",
                },
                {
                    "name": "Warehouse 2",
                    "company_id": companies.ids[1],
                    "code": "WHC2",
                },
            ]
        )
        warehouse = warehouses[0]
        warehouse.delivery_steps = "pick_ship"
        user = new_test_user(
            self.env,
            login="bub",
            groups="stock.group_stock_user",
            company_id=companies.ids[1],
            company_ids=[Command.set(companies.ids)],
        )
        pick = (
            self.env["stock.picking"]
            .with_user(user)
            .create(
                {
                    "partner_id": self.partner.id,
                    "picking_type_id": warehouse.pick_type_id.id,
                    "location_id": warehouse.lot_stock_id.id,
                    "location_dest_id": warehouse.wh_output_stock_loc_id.id,
                    "company_id": companies.ids[0],
                    "move_ids": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_uom_qty": 1,
                                "product_uom_id": self.product.uom_id.id,
                                "company_id": companies.ids[0],
                                "location_id": warehouse.lot_stock_id.id,
                                "location_dest_id": warehouse.wh_output_stock_loc_id.id,
                            }
                        )
                    ],
                }
            )
        )
        pick.with_user(user).action_confirm()
        pick.with_user(user).button_validate()
        ship = pick.move_ids.move_dest_ids
        self.assertRecordValues(
            ship,
            [
                {
                    "picking_type_id": warehouse.out_type_id.id,
                    "company_id": companies.ids[0],
                    "location_id": warehouse.wh_output_stock_loc_id.id,
                }
            ],
        )

    def test_sequence_preservation_on_step_change(self):
        out_type = self.warehouse_1.out_type_id
        sequence = out_type.sequence_id
        end_of_prefix = "LOREM/"
        sequence.prefix += end_of_prefix
        self.warehouse_1.delivery_steps = "pick_ship"
        self.assertTrue(sequence.prefix.endswith(end_of_prefix))

    def test_modified_global_route(self):
        company_2 = self.env["res.company"].create({"name": "Company 2"})

        mto_route = self.warehouse_1.mto_pull_id.route_id
        mto_route.rule_ids.unlink()
        mto_route.write(
            {"name": "New Name (MTO)", "company_id": self.warehouse_1.company_id.id}
        )

        self.env["stock.warehouse"].with_company(company_2).create(
            {"name": "Warehouse 2", "code": "2"}
        )

        route_sudo = self.env["stock.route"].sudo().with_context(active_test=False)
        renamed_route_count = route_sudo.search_count([("name", "=", "New Name (MTO)")])
        self.assertEqual(renamed_route_count, 1)

        new_mto_route = route_sudo.search([("name", "=", "Replenish on Order (MTO)")])
        self.assertEqual(len(new_mto_route), 1)
        self.assertEqual(new_mto_route.company_id.id, company_2.id)

    def test_search_qty_to_order_of_0(self):
        self.env["stock.warehouse.orderpoint"].search([]).write({"active": False})
        orderpoints = self.env["stock.warehouse.orderpoint"].create(
            [
                {
                    "location_id": self.warehouse_1.lot_stock_id.id,
                    "product_id": self.product_1.id,
                    "product_min_qty": 0.0,
                    "product_max_qty": 0.0,
                    "trigger": "manual",
                },
                {
                    "location_id": self.warehouse_1.lot_stock_id.id,
                    "product_id": self.product_2.id,
                    "product_min_qty": 3.0,
                    "product_max_qty": 5.0,
                    "trigger": "manual",
                },
            ]
        )

        for op, expected in [
            ("=", orderpoints[0]),
            (">", orderpoints[1]),
            (">=", orderpoints),
            ("<", self.env["stock.warehouse.orderpoint"]),
        ]:
            res = self.env["stock.warehouse.orderpoint"].search(
                [("qty_to_order", op, 0)]
            )
            self.assertEqual(res, expected, "Error with operator %s" % op)

        orderpoints[0].qty_to_order = 3

        for op, expected in [
            ("!=", orderpoints),
            ("=", self.env["stock.warehouse.orderpoint"]),
        ]:
            res = self.env["stock.warehouse.orderpoint"].search(
                [("qty_to_order", op, 0)]
            )
            self.assertEqual(res, expected, "Error with operator %s" % op)

    @contextmanager
    def _without_archive_guards(self):
        # these tests are about the multi-warehouse group, and archiving every
        # warehouse also meets whatever transfers and stock the database holds
        with (
            patch.object(type(self.env["stock.warehouse"]), "_check_archivable"),
            patch.object(type(self.env["stock.location"]), "_check_archivable"),
        ):
            yield

    def test_create_second_warehouse_as_stock_manager(self):
        Warehouse = self.env["stock.warehouse"]
        group_user = self.env.ref("base.group_user")
        multi_wh = self.env.ref("stock.group_stock_multi_warehouses")
        multi_loc = self.env.ref("stock.group_stock_multi_locations")
        manager = new_test_user(
            self.env, login="wh_manager", groups="stock.group_stock_manager"
        )
        self.assertFalse(manager.has_group("base.group_system"))

        branches = [
            ("res.config.settings branch", [(3, multi_wh.id), (3, multi_loc.id)]),
            ("res.groups branch", [(3, multi_wh.id), (4, multi_loc.id)]),
        ]
        for index, (label, implied) in enumerate(branches):
            with self.subTest(branch=label), self._without_archive_guards():
                Warehouse.search([]).write({"active": False})
                group_user.write({"implied_ids": implied})
                self.assertNotIn(multi_wh, group_user.implied_ids)
                base = Warehouse.create(
                    {"name": "Base WH %d" % index, "code": "BSW%d" % index}
                )
                self.assertNotIn(
                    multi_wh,
                    group_user.implied_ids,
                    "one warehouse must not imply the multi-warehouse group",
                )

                warehouse = Warehouse.with_user(manager).create(
                    {"name": "Manager WH %d" % index, "code": "MGW%d" % index}
                )
                self.assertTrue(warehouse.exists())
                self.assertIn(
                    multi_wh,
                    group_user.implied_ids,
                    "the second warehouse must imply the multi-warehouse group",
                )
                (warehouse | base).write({"active": False})

    def test_multiwarehouse_group_dropped_when_last_archived(self):
        Warehouse = self.env["stock.warehouse"]
        group_user = self.env.ref("base.group_user")
        multi_wh = self.env.ref("stock.group_stock_multi_warehouses")
        Warehouse.create({"name": "Second one", "code": "SEC"})
        self.assertIn(multi_wh, group_user.implied_ids)

        with self._without_archive_guards():
            Warehouse.search([]).action_archive()
        self.assertEqual(Warehouse.search_count([]), 0)
        self.assertNotIn(
            multi_wh,
            group_user.implied_ids,
            "no active warehouse at all must not leave the multi-warehouse UI on",
        )

    def test_write_active_true_on_active_warehouse_with_open_moves(self):
        warehouse = self.env["stock.warehouse"].create({"name": "Busy", "code": "BSY"})
        self.env["stock.move"].create(
            {
                "product_id": self.product_1.id,
                "product_uom_qty": 3,
                "picking_type_id": warehouse.int_type_id.id,
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": warehouse.lot_stock_id.id,
                "company_id": warehouse.company_id.id,
            }
        )
        warehouse.write({"active": True})
        self.assertTrue(warehouse.active)
        with self.assertRaises(UserError):
            warehouse.action_archive()

    def test_unarchive_with_foreign_picking_type(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Comes Back", "code": "CMB"}
        )
        warehouse.action_archive()
        self.env["stock.picking.type"].create(
            {
                "name": "Foreign type",
                "code": "internal",
                "sequence_code": "FGN",
                "default_location_src_id": warehouse.lot_stock_id.id,
                "default_location_dest_id": warehouse.lot_stock_id.id,
                "company_id": warehouse.company_id.id,
            }
        )
        warehouse.action_unarchive()
        self.assertTrue(warehouse.active)
        self.assertTrue(warehouse.lot_stock_id.active)

    def test_rule_names_follow_code_change(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Recode", "code": "RC1", "reception_steps": "two_steps"}
        )
        rules = (
            warehouse.reception_route_id.rule_ids
            | warehouse.delivery_route_id.rule_ids
            | warehouse.mto_pull_id
        )
        self.assertTrue(all(rule.name.startswith("RC1: ") for rule in rules))

        warehouse.write({"code": "RC2"})
        for rule in rules:
            self.assertTrue(
                rule.name.startswith("RC2: "),
                "rule %r still carries the old warehouse code" % rule.name,
            )
        self.assertEqual(warehouse.int_type_id.barcode, "RC2INT")
        self.assertEqual(warehouse.int_type_id.sequence_id.prefix, "RC2/INT/")
        self.assertEqual(warehouse.view_location_id.name, "RC2")

    def test_recode_renames_view_location_when_stock_is_nested(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Nested", "code": "NS1"}
        )
        zone = self.env["stock.location"].create(
            {
                "name": "Zone A",
                "usage": "view",
                "location_id": warehouse.view_location_id.id,
            }
        )
        warehouse.lot_stock_id.location_id = zone
        warehouse.write({"code": "NS2"})
        self.assertEqual(warehouse.view_location_id.name, "NS2")
        self.assertEqual(
            zone.name, "Zone A", "the intermediate zone must be left alone"
        )

    def test_resupply_route_name_follows_rename(self):
        Warehouse = self.env["stock.warehouse"]
        supplier = Warehouse.create({"name": "Alpha", "code": "ALP"})
        supplied = Warehouse.create({"name": "Beta", "code": "BET"})
        supplied.resupply_wh_ids = [Command.link(supplier.id)]
        route = supplied.resupply_route_ids
        self.assertEqual(route.name, "Beta: Supply Product from Alpha")

        supplier.write({"name": "Alpha Renamed"})
        self.assertEqual(route.name, "Beta: Supply Product from Alpha Renamed")
        supplied.write({"name": "Beta Renamed"})
        self.assertEqual(route.name, "Beta Renamed: Supply Product from Alpha Renamed")

    def test_warehouse_cannot_resupply_itself(self):
        warehouse = self.env["stock.warehouse"].create({"name": "Solo", "code": "SLO"})
        with self.assertRaises(ValidationError):
            warehouse.resupply_wh_ids = [Command.set([warehouse.id])]

    def test_copy_warehouse_does_not_share_locations(self):
        source = self.env["stock.warehouse"].create({"name": "Original", "code": "ORG"})
        duplicate = source.copy()
        for field in (
            "view_location_id",
            "lot_stock_id",
            "wh_input_stock_loc_id",
            "wh_qc_stock_loc_id",
            "wh_output_stock_loc_id",
            "wh_pack_stock_loc_id",
        ):
            self.assertTrue(duplicate[field])
            self.assertNotEqual(
                duplicate[field], source[field], "copies must not share %s" % field
            )

    def test_create_honours_explicit_locations(self):
        Location = self.env["stock.location"]
        view = Location.create({"name": "BYO view", "usage": "view"})
        stock = Location.create(
            {"name": "BYO stock", "usage": "internal", "location_id": view.id}
        )
        warehouse = self.env["stock.warehouse"].create(
            {
                "name": "Bring your own",
                "code": "BYO",
                "view_location_id": view.id,
                "lot_stock_id": stock.id,
            }
        )
        self.assertEqual(warehouse.view_location_id, view)
        self.assertEqual(warehouse.lot_stock_id, stock)
        self.assertTrue(warehouse.wh_input_stock_loc_id)
        self.assertEqual(warehouse.wh_input_stock_loc_id.location_id, view)

    def test_partner_locations_raise_when_either_is_missing(self):
        Warehouse = self.env["stock.warehouse"]
        customer_loc, supplier_loc = Warehouse._get_partner_locations()
        self.assertTrue(customer_loc)
        self.assertTrue(supplier_loc)

        self.env["ir.model.data"].search(
            [("module", "=", "stock"), ("name", "=", "stock_location_suppliers")]
        ).unlink()
        self.env.registry.clear_cache()
        self.env["stock.location"].with_context(active_test=False).search(
            [("usage", "=", "supplier")]
        ).usage = "transit"
        with self.assertRaises(UserError):
            Warehouse._get_partner_locations()

    def test_missing_location_rebuilt_for_current_steps(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Rebuild", "code": "RBD", "reception_steps": "three_steps"}
        )
        self.assertTrue(warehouse.wh_qc_stock_loc_id.active)
        self.env.cr.execute(
            "UPDATE stock_warehouse SET wh_qc_stock_loc_id = NULL WHERE id = %s",
            (warehouse.id,),
        )
        warehouse.invalidate_recordset(["wh_qc_stock_loc_id"])

        warehouse.write({"sequence": warehouse.sequence + 1})
        rebuilt = warehouse.with_context(active_test=False).wh_qc_stock_loc_id
        self.assertTrue(rebuilt)
        self.assertTrue(
            rebuilt.active,
            "a three-steps warehouse must not get an archived QC location",
        )

    def test_picking_type_sequences_are_unique_per_warehouse(self):
        warehouse = self.env["stock.warehouse"].create({"name": "Seqs", "code": "SQU"})
        picking_types = (
            self.env["stock.picking.type"]
            .with_context(active_test=False)
            .search([("warehouse_id", "=", warehouse.id)])
        )
        codes = warehouse._get_picking_type_codes()
        self.assertEqual(
            len(picking_types),
            len(codes),
            "every registered picking type must have been created",
        )
        self.assertEqual(
            set(picking_types.mapped("sequence_code")),
            set(codes.values()),
            "the created types must be exactly the registered ones",
        )
        orderings = picking_types.mapped("sequence")
        self.assertEqual(
            len(set(orderings)),
            len(orderings),
            "picking types share a kanban ordering: %s"
            % sorted(
                zip(orderings, picking_types.mapped("sequence_code"), strict=True)
            ),
        )
        reference_sequences = picking_types.sudo().sequence_id
        self.assertEqual(
            len(reference_sequences),
            len(picking_types),
            "every operation type must own a reference sequence of its own",
        )
        names = reference_sequences.mapped("name")
        self.assertEqual(
            len(set(names)),
            len(names),
            "two operation types of one warehouse share a sequence name: %s"
            % sorted(names),
        )

    def test_reference_sequence_names_survive_a_rename(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Flip Test", "code": "FLIP"}
        )
        picking_types = (
            self.env["stock.picking.type"]
            .with_context(active_test=False)
            .search([("warehouse_id", "=", warehouse.id)])
        )
        self.env.flush_all()

        def stored():
            picking_types.invalidate_recordset()
            return {
                picking_type.sequence_code: picking_type.sudo().sequence_id.name
                for picking_type in picking_types
            }

        def wanted():
            return {
                picking_type.sequence_code: picking_type._prepare_sequence_vals()[
                    "name"
                ]
                for picking_type in picking_types
            }

        self.assertEqual(stored(), wanted(), "created against a foreign declaration")
        warehouse.write({"name": "Flip Test 2"})
        self.env.flush_all()
        self.assertEqual(stored(), wanted(), "a rename must not flip the spelling")
        warehouse.write({"code": "FLIP2"})
        self.env.flush_all()
        self.assertEqual(stored(), wanted(), "a recode must not flip the spelling")
        self.assertTrue(
            all(
                prefix.startswith("FLIP2/")
                for prefix in picking_types.sudo().sequence_id.mapped("prefix")
            ),
            "the recode must reach every prefix",
        )

    def test_a_sequence_is_written_once_on_create(self):
        IrSequence = type(self.env["ir.sequence"])
        original = IrSequence.write
        rewritten = []

        def spy(records, vals):
            if "name" in vals:
                rewritten.extend(
                    (record.name, vals["name"])
                    for record in records
                    if record.name != vals["name"]
                )
            return original(records, vals)

        self.patch(IrSequence, "write", spy)
        self.env["stock.warehouse"].create({"name": "Once", "code": "ONCE"})
        self.env.flush_all()
        self.assertFalse(
            rewritten,
            "a reference sequence was renamed right after being created: %s"
            % rewritten,
        )

    def test_picking_type_declarations_agree(self):
        warehouse = self.warehouse_1
        codes = warehouse._get_picking_type_codes()
        self.assertEqual(set(warehouse._prepare_picking_type_create_vals()), set(codes))
        self.assertEqual(set(warehouse._prepare_picking_type_update_vals()), set(codes))
        self.assertEqual(
            set(warehouse._get_picking_type_barcode_suffixes()), set(codes)
        )

        with self.assertRaises(ValueError):
            warehouse._check_picking_type_registry(
                {key: {} for key in codes},
                {key: {} for key in codes},
                {key: {} for key in codes},
                dict(codes, unregistered_type_id="ZZZ"),
            )

    def test_route_trigger_fields_are_declared(self):
        warehouse = self.warehouse_1
        collected = {
            depend
            for values in (
                *warehouse._prepare_route_vals().values(),
                *warehouse._prepare_global_route_rule_vals().values(),
            )
            for depend in values.get("depends", [])
        }
        self.assertEqual(
            collected,
            set(warehouse._get_fields_route_trigger()),
            "a payload builder reads a field _get_fields_route_trigger does not "
            "declare, or the declaration names a field nothing reads",
        )
        self.assertEqual(
            set(warehouse._prepare_global_route_rule_vals()),
            set(warehouse._get_global_rule_fields()),
            "_get_global_rule_fields and _prepare_global_route_rule_vals disagree",
        )

    def test_a_reconfigured_warehouse_matches_a_fresh_one(self):
        Warehouse = self.env["stock.warehouse"]
        configs = [
            (reception, delivery)
            for reception in ("one_step", "two_steps", "three_steps")
            for delivery in ("ship_only", "pick_ship", "pick_pack_ship")
        ]

        def snapshot(warehouse):
            rules = (
                self.env["stock.rule"]
                .with_context(active_test=False)
                .search([("warehouse_id", "=", warehouse.id), ("active", "=", True)])
            )
            listing = {}
            for rule in rules:
                key = (
                    rule.picking_type_id.sequence_code,
                    rule.location_src_id.name,
                    rule.location_dest_id.name,
                    rule.action,
                )
                listing.setdefault(key, []).append(
                    (
                        rule.procure_method,
                        rule.auto,
                        rule.propagate_cancel,
                        rule.propagate_carrier,
                    )
                )
            return {key: sorted(value) for key, value in listing.items()}

        reference = {}
        for index, (reception, delivery) in enumerate(configs):
            reference[(reception, delivery)] = snapshot(
                Warehouse.create(
                    {
                        "name": "Ref %d" % index,
                        "code": "RF%d" % index,
                        "reception_steps": reception,
                        "delivery_steps": delivery,
                    }
                )
            )

        walker = Warehouse.create({"name": "Walker", "code": "WLK"})
        for reception, delivery in configs:
            walker.write({"reception_steps": reception, "delivery_steps": delivery})
            self.assertEqual(
                snapshot(walker),
                reference[(reception, delivery)],
                "arriving at %s/%s left rules a fresh warehouse does not have"
                % (reception, delivery),
            )

    def test_deleting_a_warehouse_reports_a_foreign_operation_type(self):
        Warehouse = self.env["stock.warehouse"]
        target = Warehouse.create({"name": "Target", "code": "TGT"})
        other = Warehouse.create({"name": "Other", "code": "OTH"})
        other.int_type_id.default_location_src_id = target.lot_stock_id.id
        other.int_type_id.active = False
        self.env.flush_all()

        with self.assertRaises(UserError) as archiving:
            target.write({"active": False})
        self.assertIn("cannot archive it", str(archiving.exception))

        with self.assertRaises(UserError) as deleting:
            target.unlink()
        self.assertIn("cannot delete it", str(deleting.exception))

    def test_a_warehouse_address_keeps_its_locations_without_a_transit(self):
        vendor = self.env["res.partner"].create({"name": "Acme Supplies"})
        supplier_location = self.env.ref("stock.stock_location_suppliers")
        vendor.with_company(self.env.company)._update_stock_property_locations(
            supplier_location
        )
        self.env.company.internal_transit_location_id = False
        self.env.flush_all()

        self.env["stock.warehouse"].create(
            {"name": "No Transit", "code": "NOTR", "partner_id": vendor.id}
        )
        self.env.flush_all()
        vendor.invalidate_recordset()
        self.assertEqual(
            vendor.with_company(self.env.company).property_stock_supplier,
            supplier_location,
            "the warehouse blanked the partner's vendor location",
        )

    def test_archiving_keeps_a_hand_granted_multi_warehouse_group(self):
        Warehouse = self.env["stock.warehouse"]
        if Warehouse.search_count([]) > 1:
            self.skipTest("needs a single-warehouse database")
        group_user = self.env.ref("base.group_user")
        group_multi = self.env.ref("stock.group_stock_multi_warehouses")
        holder = new_test_user(self.env, login="multi_wh_holder")
        group_multi.sudo().write({"user_ids": [Command.link(holder.id)]})

        extra = Warehouse.create({"name": "Second", "code": "SND"})
        self.env.flush_all()
        self.assertIn(group_multi, group_user.implied_ids)

        extra.write({"active": False})
        self.env.flush_all()
        group_user.invalidate_recordset()
        group_multi.invalidate_recordset()
        self.assertNotIn(
            group_multi,
            group_user.implied_ids,
            "the implication must go with the second warehouse",
        )
        self.assertIn(
            holder,
            group_multi.sudo().user_ids,
            "a deliberate grant must survive archiving a warehouse",
        )

    def test_a_sub_location_must_live_inside_its_warehouse(self):
        Warehouse = self.env["stock.warehouse"]
        first = Warehouse.create({"name": "Inside A", "code": "INA"})
        second = Warehouse.create({"name": "Inside B", "code": "INB"})
        with self.assertRaises(ValidationError):
            first.write({"lot_stock_id": second.lot_stock_id.id})

    def test_a_rename_writes_each_reference_sequence_at_most_once(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Renamed", "code": "RNM"}
        )
        self.env.flush_all()
        IrSequence = type(self.env["ir.sequence"])
        original = IrSequence.write
        written = []

        def spy(records, vals):
            written.extend(records.ids)
            return original(records, vals)

        self.patch(IrSequence, "write", spy)
        warehouse.write({"name": "Renamed Twice"})
        self.env.flush_all()
        self.assertEqual(
            len(written),
            len(set(written)),
            "a reference sequence was written more than once for one rename",
        )

    def _cost(self, work):
        self.env.flush_all()
        before = self.env.cr.sql_statement_count
        work()
        self.env.flush_all()
        return self.env.cr.sql_statement_count - before

    def test_creating_warehouses_in_a_batch_is_never_worse_per_warehouse(self):
        Warehouse = self.env["stock.warehouse"]
        Warehouse.create({"name": "Warm A", "code": "WMA"})
        Warehouse.create({"name": "Warm B", "code": "WMB"})

        single = self._cost(lambda: Warehouse.create({"name": "Single", "code": "SGL"}))
        batch = self._cost(
            lambda: Warehouse.create(
                [{"name": "Batch %d" % i, "code": "BT%d" % i} for i in range(5)]
            )
        )
        self.assertLessEqual(
            batch,
            5 * single,
            "creating 5 warehouses in one call cost %d queries, more than the %d "
            "that 5 separate creates would (%d each)" % (batch, 5 * single, single),
        )

    def test_the_cost_of_a_warehouse_does_not_grow_with_the_batch(self):
        Warehouse = self.env["stock.warehouse"]
        Warehouse.create({"name": "Warm C", "code": "WMC"})
        Warehouse.create({"name": "Warm D", "code": "WMD"})

        small = self._cost(
            lambda: Warehouse.create(
                [{"name": "Small %d" % i, "code": "SM%d" % i} for i in range(2)]
            )
        )
        large = self._cost(
            lambda: Warehouse.create(
                [{"name": "Large %d" % i, "code": "LG%d" % i} for i in range(6)]
            )
        )
        self.assertLessEqual(
            large / 6.0,
            small / 2.0,
            "a warehouse costs %.1f queries in a batch of 6 but %.1f in a batch "
            "of 2, so something in create scales with the batch"
            % (large / 6.0, small / 2.0),
        )

    def test_an_unrelated_write_does_not_regenerate_the_warehouse(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Untouched", "code": "UNT"}
        )
        self.env.flush_all()
        cost = self._cost(lambda: warehouse.write({"sequence": 42}))
        self.assertLessEqual(
            cost,
            8,
            "writing `sequence` cost %d queries; it triggers no route, rule, "
            "operation type or sequence work and should be close to the write "
            "itself" % cost,
        )

    def test_a_resupply_route_keeps_its_rules_across_a_round_trip(self):
        Warehouse = self.env["stock.warehouse"]
        Route = self.env["stock.route"]
        supplied = Warehouse.create({"name": "Supplied", "code": "SUP"})
        supplier = Warehouse.create({"name": "Supplier", "code": "SPL"})

        supplied.write({"resupply_wh_ids": [Command.set(supplier.ids)]})
        route = Route.search([("supplied_wh_id", "=", supplied.id)])
        self.assertTrue(route.active)
        created_rules = route.rule_ids
        self.assertTrue(created_rules, "a resupply route must carry rules")

        supplied.write({"resupply_wh_ids": [Command.clear()]})
        route = Route.with_context(active_test=False).search(
            [("supplied_wh_id", "=", supplied.id)]
        )
        self.assertFalse(route.active, "removing the supplier archives the route")
        self.assertFalse(
            route.with_context(active_test=False).rule_ids.filtered("active"),
            "and archives its rules with it",
        )

        supplied.write({"resupply_wh_ids": [Command.set(supplier.ids)]})
        route.invalidate_recordset()
        self.assertTrue(route.active, "re-adding the supplier revives the route")
        revived = route.rule_ids
        self.assertEqual(
            revived,
            created_rules,
            "the revived route must carry the rules it was archived with, not a "
            "second set and not none",
        )
        self.assertTrue(all(revived.mapped("active")))

    def _drop_partner_location_xmlid(self, name):
        self.env["ir.model.data"].search(
            [("module", "=", "stock"), ("name", "=", name)]
        ).unlink()
        self.env.registry.clear_cache()

    def test_incoming_picking_type_survives_a_missing_supplier_xmlid(self):
        supplier_loc = self.env.ref("stock.stock_location_suppliers")
        self._drop_partner_location_xmlid("stock_location_suppliers")

        picking_type = self.env["stock.picking.type"].create(
            {
                "name": "Fallback receipt",
                "code": "incoming",
                "sequence_code": "FBR",
                "warehouse_id": self.warehouse_1.id,
                "company_id": self.warehouse_1.company_id.id,
            }
        )
        self.assertEqual(picking_type.default_location_src_id, supplier_loc)

    def test_outgoing_picking_type_survives_a_missing_customer_xmlid(self):
        customer_loc = self.env.ref("stock.stock_location_customers")
        self._drop_partner_location_xmlid("stock_location_customers")

        picking_type = self.env["stock.picking.type"].create(
            {
                "name": "Fallback delivery",
                "code": "outgoing",
                "sequence_code": "FBD",
                "warehouse_id": self.warehouse_1.id,
                "company_id": self.warehouse_1.company_id.id,
            }
        )
        self.assertEqual(picking_type.default_location_dest_id, customer_loc)

    def test_missing_supplier_location_is_reported_as_itself(self):
        self._drop_partner_location_xmlid("stock_location_suppliers")
        self.env["stock.location"].with_context(active_test=False).search(
            [("usage", "=", "supplier")]
        ).usage = "transit"

        with self.assertRaises(UserError):
            self.env["stock.picking.type"].create(
                {
                    "name": "Doomed receipt",
                    "code": "incoming",
                    "sequence_code": "DMR",
                    "warehouse_id": self.warehouse_1.id,
                    "company_id": self.warehouse_1.company_id.id,
                }
            )

    def test_partner_location_names_the_missing_side(self):
        Warehouse = self.env["stock.warehouse"]
        self.assertTrue(Warehouse._get_partner_location("customer"))
        self.assertTrue(Warehouse._get_partner_location("supplier"))

        self._drop_partner_location_xmlid("stock_location_suppliers")
        self.env["stock.location"].with_context(active_test=False).search(
            [("usage", "=", "supplier")]
        ).usage = "transit"
        self.assertTrue(Warehouse._get_partner_location("customer"))
        with self.assertRaises(UserError) as caught:
            Warehouse._get_partner_location("supplier")
        self.assertIn("supplier", str(caught.exception))

    def test_unlink_takes_down_what_create_built(self):
        Location = self.env["stock.location"].with_context(active_test=False)
        PickingType = self.env["stock.picking.type"].with_context(active_test=False)
        Rule = self.env["stock.rule"].with_context(active_test=False)
        Route = self.env["stock.route"].with_context(active_test=False)

        warehouse = self.env["stock.warehouse"].create(
            {"name": "Doomed", "code": "DOOM"}
        )
        self.env.flush_all()
        locations = Location.search(
            [("id", "child_of", warehouse.view_location_id.id)]
        ).ids
        picking_types = PickingType.search([("warehouse_id", "=", warehouse.id)])
        sequences = picking_types.sequence_id.ids
        rules = Rule.search([("warehouse_id", "=", warehouse.id)]).ids
        routes = (warehouse.reception_route_id | warehouse.delivery_route_id).ids
        self.assertTrue(picking_types and sequences and rules and routes)

        warehouse.unlink()
        self.env.flush_all()

        self.assertFalse(Location.browse(locations).exists())
        self.assertFalse(picking_types.exists())
        self.assertFalse(self.env["ir.sequence"].browse(sequences).exists())
        self.assertFalse(Rule.browse(rules).exists())
        self.assertFalse(Route.browse(routes).exists())

    def test_unlink_refuses_a_warehouse_still_in_use(self):
        warehouse = self.env["stock.warehouse"].create({"name": "Busy", "code": "BUSY"})
        product = self.env["product.product"].create(
            {"name": "Busy product", "is_storable": True}
        )
        self.env["stock.quant"]._update_available_quantity(
            product, warehouse.lot_stock_id, 5
        )
        self.env.flush_all()
        with self.assertRaises(UserError) as caught:
            warehouse.unlink()
        self.assertIn("Busy", str(caught.exception))
        self.assertTrue(warehouse.exists())

    def test_unlink_leaves_a_route_another_warehouse_shares(self):
        first = self.env["stock.warehouse"].create({"name": "Share A", "code": "SHRA"})
        second = self.env["stock.warehouse"].create({"name": "Share B", "code": "SHRB"})
        self.env.flush_all()
        shared = first.reception_route_id
        shared.warehouse_ids = [Command.link(second.id)]
        self.env.flush_all()
        first.unlink()
        self.env.flush_all()
        self.assertTrue(shared.exists(), "a shared route must survive")

    def _mto_transit_rules(self, supplier):
        return (
            self.env["stock.rule"]
            .with_context(active_test=False)
            .search(
                [
                    ("route_id", "=", self.env.ref("stock.route_warehouse0_mto").id),
                    ("location_src_id", "=", supplier.lot_stock_id.id),
                    ("location_dest_id.usage", "=", "transit"),
                ]
            )
        )

    def test_resupply_mto_rule_is_not_duplicated_per_supplied_warehouse(self):
        Warehouse = self.env["stock.warehouse"]
        supplier = Warehouse.create({"name": "MTO supplier", "code": "MTOS"})
        self.env.flush_all()
        self.assertFalse(self._mto_transit_rules(supplier))
        supplied = Warehouse.browse()
        for code in ("MTOA", "MTOB", "MTOC"):
            supplied |= Warehouse.create(
                {
                    "name": "supplied " + code,
                    "code": code,
                    "resupply_wh_ids": [Command.link(supplier.id)],
                }
            )
            self.env.flush_all()
            self.assertEqual(
                len(self._mto_transit_rules(supplier)),
                1,
                "supplying %s added a duplicate MTO rule" % code,
            )
        self.assertEqual(len(supplied), 3)

    def test_resupply_mto_rule_survives_a_delivery_step_round_trip(self):
        Warehouse = self.env["stock.warehouse"]
        supplier = Warehouse.create({"name": "Round supplier", "code": "RNDS"})
        Warehouse.create(
            {
                "name": "Round supplied",
                "code": "RNDD",
                "resupply_wh_ids": [Command.link(supplier.id)],
            }
        )
        self.env.flush_all()
        self.assertEqual(len(self._mto_transit_rules(supplier)), 1)
        for steps in ("pick_ship", "ship_only", "pick_ship", "ship_only"):
            supplier.delivery_steps = steps
            self.env.flush_all()
            rules = self._mto_transit_rules(supplier)
            self.assertEqual(
                len(rules), 1, "moving to %s added a duplicate MTO rule" % steps
            )
            self.assertEqual(
                rules.active,
                steps == "ship_only",
                "the MTO rule belongs to single-step delivery only",
            )

    def test_location_barcodes_follow_a_recode(self):
        location_fields = (
            "lot_stock_id",
            "wh_input_stock_loc_id",
            "wh_qc_stock_loc_id",
            "wh_output_stock_loc_id",
            "wh_pack_stock_loc_id",
        )
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Recoded", "code": "RCA"}
        )
        self.env.flush_all()
        self.assertEqual(warehouse.lot_stock_id.barcode, "RCASTOCK")

        warehouse.write({"code": "RCB"})
        self.env.flush_all()
        for field_name in location_fields:
            barcode = warehouse[field_name].barcode
            self.assertTrue(
                barcode.startswith("RCB"),
                "%s kept the old barcode %r" % (field_name, barcode),
            )

        reuser = self.env["stock.warehouse"].create({"name": "Reuser", "code": "RCA"})
        self.env.flush_all()
        for field_name in location_fields:
            self.assertTrue(
                reuser[field_name].barcode,
                "%s was blanked by a barcode the recode should have freed" % field_name,
            )

    def test_picking_type_identifiers_come_from_one_declaration(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Stamped", "code": "STMP"}
        )
        self.env.flush_all()
        codes = warehouse._get_picking_type_codes()
        suffixes = warehouse._get_picking_type_barcode_suffixes()
        self.assertEqual(set(suffixes), set(codes))
        for field_name, sequence_code in codes.items():
            picking_type = warehouse[field_name]
            self.assertEqual(
                picking_type.barcode, "STMP" + suffixes[field_name], field_name
            )
            self.assertEqual(
                picking_type.sequence_id.prefix,
                "STMP/%s/" % sequence_code,
                field_name,
            )

    def test_second_warehouse_implies_the_groups_without_a_settings_replay(self):
        Warehouse = self.env["stock.warehouse"]
        if Warehouse.search_count([]) > 1:
            self.skipTest("needs a single-warehouse database")
        group_user = self.env.ref("base.group_user")
        multi_warehouses = self.env.ref("stock.group_stock_multi_warehouses")
        multi_locations = self.env.ref("stock.group_stock_multi_locations")
        self.assertNotIn(multi_warehouses, group_user.implied_ids)
        first = Warehouse.search([], limit=1)
        self.assertFalse(first.int_type_id.active)

        second = Warehouse.create({"name": "Second", "code": "SCND"})
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertIn(multi_warehouses, group_user.implied_ids)
        self.assertIn(multi_locations, group_user.implied_ids)
        self.assertTrue(first.int_type_id.active)
        self.assertTrue(second.int_type_id.active)

    def _resupply_routes(self, warehouses):
        return (
            self.env["stock.route"]
            .with_context(active_test=False)
            .search(
                [
                    "|",
                    ("supplied_wh_id", "in", warehouses.ids),
                    ("supplier_wh_id", "in", warehouses.ids),
                ]
            )
        )

    def test_archiving_a_warehouse_takes_its_resupply_routes_with_it(self):
        Warehouse = self.env["stock.warehouse"]
        supplier = Warehouse.create({"name": "Arch supplier", "code": "ARS"})
        supplied = Warehouse.create(
            {
                "name": "Arch supplied",
                "code": "ARD",
                "resupply_wh_ids": [Command.link(supplier.id)],
            }
        )
        other = Warehouse.create(
            {
                "name": "Arch other",
                "code": "ARO",
                "resupply_wh_ids": [Command.link(supplier.id)],
            }
        )
        self.env.flush_all()
        route = self._resupply_routes(supplied).filtered(
            lambda r: r.supplied_wh_id == supplied
        )
        other_route = self._resupply_routes(other).filtered(
            lambda r: r.supplied_wh_id == other
        )
        self.assertTrue(route.active and other_route.active)

        supplier.write({"active": False})
        self.env.flush_all()
        self.assertFalse(route.active, "the supplier's routes must go with it")
        self.assertFalse(other_route.active)

        supplier.write({"active": True})
        self.env.flush_all()
        self.assertTrue(route.active, "and come back with it")
        self.assertTrue(other_route.active)

        supplied.write({"active": False})
        self.env.flush_all()
        self.assertFalse(route.active)
        self.assertTrue(
            other_route.active, "another warehouse's route is not this one's"
        )

    def test_reactivating_does_not_revive_an_unlinked_resupply_route(self):
        Warehouse = self.env["stock.warehouse"]
        supplier = Warehouse.create({"name": "Unlink supplier", "code": "ULS"})
        supplied = Warehouse.create(
            {
                "name": "Unlink supplied",
                "code": "ULD",
                "resupply_wh_ids": [Command.link(supplier.id)],
            }
        )
        self.env.flush_all()
        route = self._resupply_routes(supplied).filtered(
            lambda r: r.supplied_wh_id == supplied
        )
        self.assertTrue(route.active)

        supplied.write({"resupply_wh_ids": [Command.unlink(supplier.id)]})
        self.env.flush_all()
        self.assertFalse(route.active)

        supplied.write({"active": False})
        self.env.flush_all()
        supplied.write({"active": True})
        self.env.flush_all()
        self.assertFalse(
            route.active, "a route whose resupply link is gone must stay archived"
        )
        self.assertFalse(
            any(route.rule_ids.mapped("active")),
            "and must not carry live rules underneath it",
        )

    def test_each_warehouse_gets_its_own_operation_type_color(self):
        Warehouse = self.env["stock.warehouse"]
        color_fields = ("in_type_id", "out_type_id", "int_type_id", "pick_type_id")
        taken = {
            picking_type.color
            for picking_type in self.env["stock.picking.type"]
            .with_context(active_test=False)
            .search(
                [
                    ("warehouse_id", "!=", False),
                    ("company_id", "=", self.env.company.id),
                ]
            )
        }
        made = Warehouse.create(
            [{"name": "Hue %d" % index, "code": "HUE%d" % index} for index in range(3)]
        )
        self.env.flush_all()
        seen = []
        for warehouse in made:
            colors = {warehouse[field].color for field in color_fields}
            self.assertEqual(
                len(colors),
                1,
                "%s spread its operation types over several colors" % warehouse.code,
            )
            color = colors.pop()
            self.assertNotIn(
                color,
                taken,
                "%s reused a color another warehouse already holds" % warehouse.code,
            )
            taken.add(color)
            seen.append(color)
        self.assertEqual(
            len(set(seen)), len(seen), "the new warehouses share a color: %s" % seen
        )

    def test_default_names_read_the_existing_ones_once_per_company(self):
        Warehouse = self.env["stock.warehouse"]
        model = type(Warehouse)
        original = model._get_existing_warehouse_values
        calls = []

        def spy(records, field_name, company, taken=()):
            calls.append(field_name)
            return original(records, field_name, company, taken)

        self.patch(model, "_get_existing_warehouse_values", spy)
        Warehouse.create([{} for _ in range(5)])
        self.env.flush_all()
        self.assertEqual(
            sorted(calls),
            ["code", "name"],
            "the existing names and codes are read once per field per company, "
            "not once per record; got %s" % calls,
        )

    def test_supplying_a_name_and_code_reads_nothing(self):
        Warehouse = self.env["stock.warehouse"]
        model = type(Warehouse)
        original = model._get_existing_warehouse_values
        calls = []

        def spy(records, field_name, company, taken=()):
            calls.append(field_name)
            return original(records, field_name, company, taken)

        self.patch(model, "_get_existing_warehouse_values", spy)
        Warehouse.create({"name": "Explicit", "code": "EXPL"})
        self.env.flush_all()
        self.assertEqual(
            calls, [], "nothing needs generating, so nothing should be read"
        )

    def test_a_settled_warehouse_rebuilds_its_routes_without_writing(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Settled", "code": "STL"}
        )
        self.env.flush_all()
        model = type(warehouse)
        original = model.write
        writes = []

        def spy(records, vals):
            writes.append(set(vals))
            return original(records, vals)

        self.patch(model, "write", spy)
        warehouse._create_or_update_route()
        self.env.flush_all()
        self.assertEqual(
            writes,
            [],
            "re-linking routes that are already linked cost a full write: %s" % writes,
        )

    def test_reactivation_replays_every_trigger_field_through_write(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Replayed", "code": "RPL"}
        )
        self.env.flush_all()
        seen = []
        model = type(warehouse)
        original = model.write

        def spy(records, vals):
            seen.append(set(vals))
            return original(records, vals)

        warehouse.action_archive()
        self.env.flush_all()
        self.patch(model, "write", spy)
        warehouse.action_unarchive()
        self.env.flush_all()

        triggers = set(warehouse._get_fields_route_trigger())
        replayed = {name for vals in seen for name in vals} & triggers
        self.assertEqual(
            replayed,
            triggers,
            "reactivation must write every trigger field so each module's write() "
            "override replays its own reconfiguration; missing: %s"
            % (triggers - replayed),
        )

    def test_a_rebuilt_operation_type_keeps_its_warehouse_color(self):
        Warehouse = self.env["stock.warehouse"]
        first, _second, third = Warehouse.create(
            [{"name": "Hue %s" % code, "code": code} for code in ("GPA", "GPB", "GPC")]
        )
        self.env.flush_all()
        expected = third.in_type_id.color

        first.unlink()
        self.env.flush_all()

        stale = third.out_type_id
        stale.barcode = False
        third.write({"out_type_id": False})
        third.write(third._create_or_update_picking_types())
        self.env.flush_all()

        self.assertEqual(
            third.out_type_id.color,
            expected,
            "the rebuilt operation type was given a fresh color instead of its "
            "warehouse's, so one warehouse now spans two colors",
        )

    def test_rebuilding_one_side_keeps_the_return_operation_type(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Returner", "code": "RTN"}
        )
        self.env.flush_all()
        incoming = warehouse.in_type_id
        self.assertEqual(warehouse.out_type_id.return_picking_type_id, incoming)
        self.assertEqual(incoming.return_picking_type_id, warehouse.out_type_id)

        stale_outgoing = warehouse.out_type_id
        stale_outgoing.barcode = False
        warehouse.write({"out_type_id": False})
        warehouse.write(warehouse._create_or_update_picking_types())
        self.env.flush_all()

        self.assertNotEqual(warehouse.out_type_id, stale_outgoing)
        self.assertEqual(
            warehouse.out_type_id.return_picking_type_id,
            incoming,
            "the rebuilt outgoing type did not point back at the surviving receipt",
        )
        self.assertEqual(
            incoming.return_picking_type_id,
            warehouse.out_type_id,
            "the receipt still points at the operation type that was replaced",
        )

    def test_a_reconfigure_leaves_a_custom_return_operation_type_alone(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Curated", "code": "CUR"}
        )
        self.env.flush_all()
        custom = self.env["stock.picking.type"].create(
            {
                "name": "Curated Return",
                "code": "incoming",
                "sequence_code": "CRT",
                "company_id": self.env.company.id,
            }
        )
        warehouse.in_type_id.return_picking_type_id = custom
        self.env.flush_all()

        warehouse.write({"reception_steps": "two_steps"})
        warehouse.write({"delivery_steps": "pick_pack_ship"})
        warehouse.write({"code": "CUX"})
        self.env.flush_all()

        self.assertEqual(
            warehouse.in_type_id.return_picking_type_id,
            custom,
            "a reconfigure re-paired operation types that it never recreated",
        )

    def test_a_squatted_operation_type_barcode_does_not_break_a_recode(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Squatted", "code": "SQA"}
        )
        squatter = self.env["stock.picking.type"].create(
            {
                "name": "Hand made",
                "code": "internal",
                "sequence_code": "HAND",
                "barcode": "SQBIN",
                "company_id": self.env.company.id,
            }
        )
        self.env.flush_all()

        warehouse.write({"code": "SQB"})
        self.env.flush_all()

        self.assertEqual(squatter.barcode, "SQBIN", "the squatter lost its barcode")
        self.assertFalse(
            warehouse.in_type_id.barcode,
            "the receipt type took a barcode another operation type already held",
        )
        self.assertEqual(
            warehouse.out_type_id.barcode,
            "SQBOUT",
            "an unclaimed barcode was dropped along with the contested one",
        )

    def test_two_records_claiming_one_barcode_do_not_reach_the_database(self):
        Warehouse = self.env["stock.warehouse"]
        values_list = [{"barcode": "TWINBC"}, {"barcode": "TWINBC"}]
        Warehouse._remove_taken_barcodes(
            "stock.picking.type", values_list, self.env.company.id
        )
        self.assertEqual(
            [values["barcode"] for values in values_list],
            ["TWINBC", False],
            "the resolver checked the database but not its own batch, so both "
            "records would reach the unique index",
        )

    def test_duplicate_barcode_suffixes_are_refused_at_declaration(self):
        warehouse = self.warehouse_1
        codes = warehouse._get_picking_type_codes()
        suffixes = dict(warehouse._get_picking_type_barcode_suffixes(codes))
        suffixes["xdock_type_id"] = suffixes["in_type_id"]
        with self.assertRaises(ValueError):
            warehouse._check_picking_type_registry(
                warehouse._prepare_picking_type_update_vals(),
                warehouse._prepare_picking_type_create_vals(),
                suffixes,
                codes,
            )

    def test_two_locations_claiming_one_barcode_do_not_reach_the_database(self):
        Warehouse = self.env["stock.warehouse"]
        model = type(Warehouse)
        original = model._prepare_sub_location_vals

        def clashing(self, vals, code=False):
            values = original(self, vals, code)
            values["wh_qc_stock_loc_id"] = dict(
                values["wh_qc_stock_loc_id"],
                barcode=values["lot_stock_id"]["barcode"],
            )
            return values

        self.patch(model, "_prepare_sub_location_vals", clashing)
        warehouse = Warehouse.create({"name": "Clashing Loc", "code": "CLL"})
        self.env.flush_all()
        self.assertEqual(warehouse.lot_stock_id.barcode, "CLLSTOCK")
        self.assertFalse(
            warehouse.wh_qc_stock_loc_id.barcode,
            "the second claimant of a barcode kept it and reached the unique index",
        )

    def test_a_step_field_without_a_default_does_not_crash_the_builder(self):
        Warehouse = self.env["stock.warehouse"]
        original = type(Warehouse)._get_fields_location_step
        self.patch(
            type(Warehouse),
            "_get_fields_location_step",
            lambda self: original(self) + ["code"],
        )
        values = Warehouse.browse()._get_location_step_values({})
        self.assertEqual(values["reception_steps"], "one_step")
        self.assertEqual(values["code"], "")

    def test_an_oversized_code_derives_names_from_what_is_stored(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Oversize", "code": "OVR"}
        )
        self.env.flush_all()
        warehouse.write({"code": "ABCDEFGH"})
        self.env.flush_all()

        stored = warehouse.code
        self.assertEqual(stored, "ABCDE", "stock.warehouse.code is a Char(5)")
        self.assertEqual(warehouse.view_location_id.name, stored)
        self.assertEqual(warehouse.lot_stock_id.barcode, stored + "STOCK")
        self.assertEqual(warehouse.in_type_id.barcode, stored + "IN")
        rule = self.env["stock.rule"].search(
            [("warehouse_id", "=", warehouse.id)], limit=1
        )
        self.assertTrue(
            rule.name.startswith(stored + ": "),
            "rule %r is prefixed by a code the warehouse does not hold" % rule.name,
        )

    def test_a_write_assigning_a_picking_type_creates_no_second_one(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Pending Types", "code": "PTY"}
        )
        qc_type = warehouse.qc_type_id
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE stock_warehouse SET wh_qc_stock_loc_id = NULL, qc_type_id = NULL"
            " WHERE id = %s",
            [warehouse.id],
        )
        self.env.invalidate_all()

        warehouse.write({"qc_type_id": qc_type.id})
        self.env.flush_all()

        self.assertEqual(warehouse.qc_type_id, qc_type)
        self.assertTrue(warehouse.wh_qc_stock_loc_id)
        self.assertEqual(
            self.env["stock.picking.type"]
            .with_context(active_test=False)
            .search_count(
                [
                    ("warehouse_id", "=", warehouse.id),
                    ("sequence_code", "=", qc_type.sequence_code),
                ]
            ),
            1,
        )
