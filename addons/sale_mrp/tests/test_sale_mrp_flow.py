import datetime

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, common
from odoo.tools import mute_logger

from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import (
    ValuationReconciliationTestCommon,
)


class TestSaleMrpFlowCommon(ValuationReconciliationTestCommon, TestSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._enable_uom()
        cls.env.ref("stock.route_warehouse0_mto").active = True

        cls.StockMove = cls.env["stock.move"]
        cls.UoM = cls.env["uom.uom"]
        cls.MrpProduction = cls.env["mrp.production"]
        cls.Quant = cls.env["stock.quant"]
        cls.ProductCategory = cls.env["product.category"]

        cls.uom_kg = cls.uom_kgm
        cls.uom_gm = cls.uom_gram
        cls.uom_ten = cls.UoM.create(
            {
                "name": "Test-Ten",
                "relative_factor": 10,
                "relative_uom_id": cls.uom_unit.id,
            }
        )

        cls.component_a = cls._cls_create_product("Comp A", cls.uom_unit)
        cls.component_b = cls._cls_create_product("Comp B", cls.uom_unit)
        cls.component_c = cls._cls_create_product("Comp C", cls.uom_unit)
        cls.component_d = cls._cls_create_product("Comp D", cls.uom_unit)
        cls.component_e = cls._cls_create_product("Comp E", cls.uom_unit)
        cls.component_f = cls._cls_create_product("Comp F", cls.uom_unit)
        cls.component_g = cls._cls_create_product("Comp G", cls.uom_unit)

        cls.kit_1 = cls._cls_create_product("Kit 1", cls.uom_unit)

        cls.bom_kit_1 = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.kit_1.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        BomLine = cls.env["mrp.bom.line"]
        BomLine.create(
            {
                "product_id": cls.component_a.id,
                "product_qty": 2.0,
                "bom_id": cls.bom_kit_1.id,
            }
        )
        BomLine.create(
            {
                "product_id": cls.component_b.id,
                "product_qty": 1.0,
                "bom_id": cls.bom_kit_1.id,
            }
        )
        BomLine.create(
            {
                "product_id": cls.component_c.id,
                "product_qty": 3.0,
                "bom_id": cls.bom_kit_1.id,
            }
        )

        cls.kit_2 = cls._cls_create_product("Kit 2", cls.uom_unit)
        cls.kit_3 = cls._cls_create_product("kit 3", cls.uom_unit)
        cls.kit_parent = cls._cls_create_product("Kit Parent", cls.uom_unit)

        bom_kit_2 = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.kit_2.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        BomLine.create(
            {
                "product_id": cls.component_d.id,
                "product_qty": 1.0,
                "bom_id": bom_kit_2.id,
            }
        )
        BomLine.create(
            {"product_id": cls.kit_1.id, "product_qty": 2.0, "bom_id": bom_kit_2.id}
        )

        bom_kit_parent = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.kit_parent.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        BomLine.create(
            {
                "product_id": cls.component_e.id,
                "product_qty": 1.0,
                "bom_id": bom_kit_parent.id,
            }
        )
        BomLine.create(
            {
                "product_id": cls.kit_2.id,
                "product_qty": 2.0,
                "bom_id": bom_kit_parent.id,
            }
        )

        bom_kit_3 = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.kit_3.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        BomLine.create(
            {
                "product_id": cls.component_f.id,
                "product_qty": 1.0,
                "bom_id": bom_kit_3.id,
            }
        )
        BomLine.create(
            {
                "product_id": cls.component_g.id,
                "product_qty": 2.0,
                "bom_id": bom_kit_3.id,
            }
        )

        BomLine.create(
            {
                "product_id": cls.kit_3.id,
                "product_qty": 2.0,
                "bom_id": bom_kit_parent.id,
            }
        )

    @classmethod
    def _cls_create_product(cls, name, uom_id, routes=()):
        p = Form(cls.env["product.product"])
        p.name = name
        p.is_storable = True
        p.uom_id = uom_id
        p.route_ids.clear()
        for r in routes:
            p.route_ids.add(r)
        return p.save()

    def _process_quantities(self, moves, quantities_to_process):
        moves_to_process = moves.filtered(
            lambda m: m.product_id in quantities_to_process
        )
        for move in moves_to_process:
            move.write(
                {"quantity": quantities_to_process[move.product_id], "picked": True}
            )

    def _assert_quantities(self, moves, quantities_to_process):
        moves_to_process = moves.filtered(
            lambda m: m.product_id in quantities_to_process
        )
        for move in moves_to_process:
            self.assertEqual(move.product_qty, quantities_to_process[move.product_id])

    def _create_move_quantities(self, qty_to_process, components, warehouse):
        for comp in components:
            f = Form(self.env["stock.move"])
            f.location_id = self.env.ref("stock.stock_location_suppliers")
            f.location_dest_id = warehouse.lot_stock_id
            f.product_id = comp
            f.product_uom_id = qty_to_process[comp][1]
            f.product_uom_qty = qty_to_process[comp][0]
            move = f.save()
            move._action_confirm()
            move._action_assign()
            move_line = move.move_line_ids[0]
            move_line.quantity = qty_to_process[comp][0]
            move._action_done()


@common.tagged("post_install", "-at_install")
class TestSaleMrpFlow(TestSaleMrpFlowCommon):
    def test_00_sale_mrp_flow(self):
        route_manufacture = self.company_data[
            "default_warehouse"
        ].manufacture_pull_id.route_id
        route_mto = self.company_data["default_warehouse"].mto_pull_id.route_id
        product_a = self._cls_create_product(
            "Product A", self.uom_unit, routes=[route_manufacture, route_mto]
        )
        product_c = self._cls_create_product("Product C", self.uom_kg)
        product_b = self._cls_create_product(
            "Product B", self.uom_dozen, routes=[route_manufacture, route_mto]
        )
        product_d = self._cls_create_product(
            "Product D", self.uom_unit, routes=[route_manufacture, route_mto]
        )

        with Form(self.env["mrp.bom"]) as f:
            f.product_tmpl_id = product_a.product_tmpl_id
            f.product_qty = 2
            f.product_uom_id = self.uom_dozen
            with f.bom_line_ids.new() as line:
                line.product_id = product_b
                line.product_qty = 3
                line.product_uom_id = self.uom_unit
            with f.bom_line_ids.new() as line:
                line.product_id = product_c
                line.product_qty = 300.0
                line.product_uom_id = self.uom_gm
            with f.bom_line_ids.new() as line:
                line.product_id = product_d
                line.product_qty = 4
                line.product_uom_id = self.uom_unit

        with Form(self.env["mrp.bom"]) as f:
            f.product_tmpl_id = product_b.product_tmpl_id
            f.product_qty = 1
            f.product_uom_id = self.uom_unit
            f.type = "phantom"
            with f.bom_line_ids.new() as line:
                line.product_id = product_c
                line.product_qty = 0.400
                line.product_uom_id = self.uom_kg

        with Form(self.env["mrp.bom"]) as f:
            f.product_tmpl_id = product_d.product_tmpl_id
            f.product_qty = 1
            f.product_uom_id = self.uom_unit
            with f.bom_line_ids.new() as line:
                line.product_id = product_c
                line.product_qty = 1
                line.product_uom_id = self.uom_kg

        order_form = Form(self.env["sale.order"])
        order_form.partner_id = self.env["res.partner"].create(
            {"name": "My Test Partner"}
        )
        with order_form.line_ids.new() as line:
            line.product_id = product_a
            line.product_uom_id = self.uom_dozen
            line.product_qty = 10
        order = order_form.save()
        order.action_confirm()

        self.assertEqual(
            order.mrp_production_count,
            1,
            "Only the top-level MO for product A is linked to the SO",
        )
        self.assertEqual(
            order.mrp_production_ids.mrp_production_child_count,
            1,
            "The top-level MO generates one child MO to manufacture the component product D",
        )

        self.env["stock.scheduler"].run()
        mnf_product_a = self.env["mrp.production"].search(
            [("product_id", "=", product_a.id)]
        )

        self.assertTrue(mnf_product_a, "Manufacturing order not created.")
        self.assertEqual(
            mnf_product_a.product_qty,
            10,
            "Wrong product quantity in manufacturing order.",
        )
        self.assertEqual(
            mnf_product_a.product_uom_id,
            self.uom_dozen,
            "Wrong unit of measure in manufacturing order.",
        )
        self.assertEqual(
            mnf_product_a.state, "confirmed", "Manufacturing order should be confirmed."
        )

        moves = self.StockMove.search(
            [
                ("raw_material_production_id", "=", mnf_product_a.id),
                ("product_id", "=", product_c.id),
                ("product_uom_id", "=", self.uom_kg.id),
            ]
        )

        self.assertEqual(
            len(moves), 1, "Production move lines are not generated proper."
        )
        list_qty = {move.product_qty for move in moves}
        self.assertEqual(
            list_qty,
            {6.0},
            "Wrong product quantity in 'To consume line' of manufacturing order.",
        )
        for move in moves:
            self.assertEqual(
                move.state,
                "confirmed",
                "Wrong state in 'To consume line' of manufacturing order.",
            )

        move = self.StockMove.search(
            [
                ("raw_material_production_id", "=", mnf_product_a.id),
                ("product_id", "=", product_c.id),
                ("product_uom_id", "=", self.uom_gm.id),
            ]
        )

        self.assertEqual(
            len(move), 1, "Production move lines are not generated proper."
        )
        self.assertEqual(
            move.product_uom_qty,
            1500.0,
            "Wrong product quantity in 'To consume line' of manufacturing order.",
        )
        self.assertEqual(
            move.state,
            "confirmed",
            "Wrong state in 'To consume line' of manufacturing order.",
        )

        move = self.StockMove.search(
            [
                ("raw_material_production_id", "=", mnf_product_a.id),
                ("product_id", "=", product_d.id),
            ]
        )

        self.assertEqual(len(move), 1, "Production lines are not generated proper.")

        mnf_product_d = self.MrpProduction.search(
            [("product_id", "=", product_d.id)], order="id desc", limit=1
        )
        self.assertEqual(
            mnf_product_d.state, "confirmed", "Manufacturing order should be confirmed."
        )

        move = self.StockMove.search(
            [
                ("raw_material_production_id", "=", mnf_product_d.id),
                ("product_id", "=", product_c.id),
            ]
        )
        self.assertEqual(
            move.product_qty,
            20,
            "Wrong product quantity in 'To consume line' of manufacturing order.",
        )
        self.assertEqual(
            move.product_uom_id.id,
            self.uom_kg.id,
            "Wrong unit of measure in 'To consume line' of manufacturing order.",
        )
        self.assertEqual(
            move.state,
            "confirmed",
            "Wrong state in 'To consume line' of manufacturing order.",
        )

        self.Quant.with_context(inventory_mode=True).create(
            {
                "product_id": product_c.id,
                "inventory_quantity": 20,
                "location_id": self.company_data["default_warehouse"].lot_stock_id.id,
            }
        ).action_apply_inventory()

        mnf_product_d.action_assign()
        self.assertEqual(
            mnf_product_d.reservation_state,
            "assigned",
            "Availability should be assigned",
        )
        self.assertEqual(
            move.state,
            "assigned",
            "Wrong state in 'To consume line' of manufacturing order.",
        )

        mo_form = Form(mnf_product_d)
        mo_form.qty_producing = 20
        mnf_product_d = mo_form.save()
        mnf_product_d.button_mark_done()

        self.assertEqual(
            mnf_product_d.state,
            "done",
            "Manufacturing order should still be in progress state.",
        )
        self.assertEqual(
            product_d.qty_available, 20, "Wrong quantity available of product D."
        )

        self.assertEqual(
            mnf_product_a.state, "confirmed", "Manufacturing order should be confirmed."
        )
        move = self.StockMove.search(
            [
                ("raw_material_production_id", "=", mnf_product_a.id),
                ("product_id", "=", product_d.id),
            ]
        )
        self.assertEqual(
            move.state,
            "assigned",
            "Wrong state in 'To consume line' of manufacturing order.",
        )

        self.Quant.with_context(inventory_mode=True).create(
            {
                "product_id": product_c.id,
                "inventory_quantity": 27.51,
                "location_id": self.company_data["default_warehouse"].lot_stock_id.id,
            }
        ).action_apply_inventory()

        mnf_product_a.action_assign()
        self.assertEqual(
            mnf_product_a.reservation_state,
            "assigned",
            "Manufacturing order inventory state should be available.",
        )
        moves = self.StockMove.search(
            [
                ("raw_material_production_id", "=", mnf_product_a.id),
                ("product_id", "=", product_c.id),
            ]
        )

        for move in moves:
            self.assertEqual(
                move.state,
                "assigned",
                "Wrong state in 'To consume line' of manufacturing order.",
            )

        mo_form = Form(mnf_product_a)
        mo_form.qty_producing = mo_form.product_qty
        mnf_product_a = mo_form.save()
        mnf_product_a._post_inventory()
        self.assertEqual(
            mnf_product_a.state,
            "done",
            "Manufacturing order should still be in the progress state.",
        )
        self.assertEqual(
            product_a.qty_available, 120, "Wrong quantity available of product A."
        )

    def test_01_sale_mrp_delivery_kit(self):
        product = self.env["product.product"].create(
            {
                "name": "Table Kit",
                "type": "consu",
                "invoice_policy": "transferred",
            }
        )
        product.write(
            {
                "route_ids": [
                    (
                        6,
                        0,
                        [
                            self.company_data[
                                "default_warehouse"
                            ].manufacture_pull_id.route_id.id
                        ],
                    )
                ]
            }
        )

        product_wood_panel = self.env["product.product"].create(
            {
                "name": "Wood Panel",
                "is_storable": True,
            }
        )
        product_desk_bolt = self.env["product.product"].create(
            {
                "name": "Bolt",
                "is_storable": True,
            }
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.product_tmpl_id.id,
                "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                "sequence": 2,
                "type": "phantom",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product_wood_panel.id,
                            "product_qty": 1,
                            "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": product_desk_bolt.id,
                            "product_qty": 4,
                            "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                        },
                    ),
                ],
            }
        )

        partner = self.env["res.partner"].create({"name": "My Test Partner"})
        if "property_delivery_carrier_id" in partner:
            partner.property_delivery_carrier_id = False

        f = Form(self.env["sale.order"])
        f.partner_id = partner
        with f.line_ids.new() as line:
            line.product_id = product
            line.product_qty = 5
        so = f.save()

        so.action_confirm()
        self.assertTrue(
            so.picking_ids,
            'Sale MRP: no picking created for "invoice on delivery" storable products',
        )

        with self.assertRaises(UserError):
            so._create_invoices()
        self.assertEqual(
            so.line_ids.invoice_state,
            "no",
            'Sale MRP: line invoice_state should be "nothing to invoice" after invoicing',
        )

        pick = so.picking_ids
        pick.move_ids.write({"quantity": 1, "picked": True})
        Form.from_action(self.env, pick.button_validate()).save().process()
        self.assertEqual(
            so.line_ids.invoice_state,
            "no",
            'Sale MRP: line invoice_state should be "no" after partial delivery of a kit',
        )
        del_qty = sum(sol.qty_transferred for sol in so.line_ids)
        self.assertEqual(
            del_qty,
            0.0,
            "Sale MRP: delivered quantity should be zero after partial delivery of a kit",
        )
        self.assertEqual(
            len(so.picking_ids), 2, "Sale MRP: number of pickings should be 2"
        )
        pick_2 = so.picking_ids.filtered("backorder_id")
        for move in pick_2.move_ids:
            if move.product_id.id == product_desk_bolt.id:
                move.write({"quantity": 19, "picked": True})
            else:
                move.write({"quantity": 4, "picked": True})
        pick_2.button_validate()

        del_qty = sum(sol.qty_transferred for sol in so.line_ids)
        self.assertEqual(
            del_qty,
            5.0,
            "Sale MRP: delivered quantity should be 5.0 after complete delivery of a kit",
        )
        self.assertEqual(
            so.line_ids.invoice_state,
            "to do",
            'Sale MRP: line invoice_state should be "to do" after complete delivery of a kit',
        )

    def test_02_sale_mrp_anglo_saxon(self):
        self.env.company.currency_id = self.env.ref("base.USD")
        self.uom_unit = self.UoM.create(
            {
                "name": "Test-Unit",
                "relative_factor": 1,
            }
        )
        self.company = self.company_data["company"]
        self.company.account_config_id.anglo_saxon_accounting = True
        self.partner = self.env["res.partner"].create({"name": "My Test Partner"})
        self.category = self.env.ref("product.product_category_goods").copy(
            {
                "name": "Test category",
                "property_valuation": "real_time",
                "property_cost_method": "fifo",
            }
        )
        self.account_receiv = self.env["account.account"].create(
            {
                "name": "Receivable",
                "code": "RCV00",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        account_expense = self.env["account.account"].create(
            {
                "name": "Expense",
                "code": "EXP00",
                "account_type": "liability_current",
                "reconcile": True,
            }
        )
        account_income = self.env["account.account"].create(
            {
                "name": "Income",
                "code": "INC00",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        account_valuation = self.env["account.account"].create(
            {
                "name": "Valuation",
                "code": "STV00",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        self.partner.property_account_receivable_id = self.account_receiv
        self.category.property_account_income_categ_id = account_income
        self.category.property_account_expense_categ_id = account_expense
        self.category.property_stock_valuation_account_id = account_valuation
        self.category.property_stock_journal = self.env["account.journal"].create(
            {"name": "Stock journal", "type": "sale", "code": "STK00"}
        )

        Product = self.env["product.product"]
        self.finished_product = Product.create(
            {
                "name": "Finished product",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
                "invoice_policy": "transferred",
                "categ_id": self.category.id,
            }
        )
        self.component1 = Product.create(
            {
                "name": "Component 1",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
                "categ_id": self.category.id,
                "standard_price": 20,
            }
        )
        self.component2 = Product.create(
            {
                "name": "Component 2",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
                "categ_id": self.category.id,
                "standard_price": 10,
            }
        )

        self.env["stock.quant"].sudo().create(
            {
                "product_id": self.component1.id,
                "location_id": self.company_data["default_warehouse"].lot_stock_id.id,
                "quantity": 6.0,
            }
        )
        self.env["stock.quant"].sudo().create(
            {
                "product_id": self.component2.id,
                "location_id": self.company_data["default_warehouse"].lot_stock_id.id,
                "quantity": 3.0,
            }
        )
        self.bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.finished_product.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )
        BomLine = self.env["mrp.bom.line"]
        BomLine.create(
            {
                "product_id": self.component1.id,
                "product_qty": 2.0,
                "bom_id": self.bom.id,
            }
        )
        BomLine.create(
            {
                "product_id": self.component2.id,
                "product_qty": 1.0,
                "bom_id": self.bom.id,
            }
        )

        so_vals = {
            "partner_id": self.partner.id,
            "partner_invoice_id": self.partner.id,
            "partner_shipping_id": self.partner.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": self.finished_product.name,
                        "product_id": self.finished_product.id,
                        "product_qty": 3,
                        "price_unit": self.finished_product.list_price,
                    },
                )
            ],
            "company_id": self.company.id,
        }
        self.so = self.env["sale.order"].create(so_vals)
        self.so.action_confirm()
        pick = self.so.picking_ids
        self.assertEqual(
            pick.move_ids.mapped("product_id"), self.component1 | self.component2
        )
        pick.button_validate()
        self.so._create_invoices()
        self.invoice = self.so.invoice_ids
        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 2.0
        self.invoice = move_form.save()
        self.invoice.action_post()
        aml = self.invoice.line_ids
        aml_expense = aml.filtered(lambda l: l.display_type == "cogs" and l.debit > 0)
        aml_output = aml.filtered(lambda l: l.display_type == "cogs" and l.credit > 0)
        self.assertEqual(
            aml_expense.debit, 100, "Cost of Good Sold entry missing or mismatching"
        )
        self.assertEqual(
            aml_output.credit, 100, "Cost of Good Sold entry missing or mismatching"
        )

    def test_03_sale_mrp_simple_kit_qty_transferred(self):

        stock_location = self.company_data["default_warehouse"].lot_stock_id
        self.env["stock.quant"]._update_available_quantity(
            self.component_a, stock_location, 20
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_b, stock_location, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_c, stock_location, 30
        )

        partner = self.env["res.partner"].create({"name": "My Test Partner"})
        f = Form(self.env["sale.order"])
        f.partner_id = partner
        with f.line_ids.new() as line:
            line.product_id = self.kit_1
            line.product_qty = 10.0

        so = f.save()
        so.action_confirm()

        self.assertEqual(len(so.picking_ids), 1)
        picking_original = so.picking_ids[0]
        move_ids = picking_original.move_ids

        self.assertEqual(len(move_ids), 3)

        bom_from_k1 = self.env["mrp.bom"]._get_bom_by_product(self.kit_1)[self.kit_1]
        self.assertEqual(self.bom_kit_1.id, bom_from_k1.id)
        self.assertEqual(bom_from_k1.type, "phantom")

        line_idss = so.line_ids
        self.assertEqual(len(line_idss), 1)
        line_ids = line_idss[0]
        self.assertEqual(line_ids.product_id.id, self.kit_1.id)
        self.assertEqual(line_ids.product_qty, 10.0)

        expected_quantities = {
            self.component_a: 20,
            self.component_b: 10,
            self.component_c: 30,
        }
        self._assert_quantities(move_ids, expected_quantities)

        picking_original.move_ids.sorted()[0].write({"quantity": 1, "picked": True})

        Form.from_action(self.env, so.picking_ids[0].button_validate()).save().process()

        self.assertEqual(len(so.picking_ids), 2)
        backorder_1 = so.picking_ids - picking_original
        self.assertEqual(backorder_1.backorder_id.id, picking_original.id)
        self.assertEqual(line_ids.qty_transferred, 0)

        backorder_1.move_ids.write({"quantity": 6, "picked": True})
        Form.from_action(self.env, backorder_1.button_validate()).save().process()

        self.assertEqual(len(so.picking_ids), 3)
        backorder_2 = so.picking_ids - picking_original - backorder_1
        self.assertEqual(backorder_2.backorder_id.id, backorder_1.id)

        self.assertEqual(line_ids.qty_transferred, 2)

        backorder_2.move_ids.write({"quantity": 3, "picked": True})

        Form.from_action(self.env, backorder_2.button_validate()).save().process()

        self.assertEqual(len(so.picking_ids), 4)
        backorder_3 = so.picking_ids - picking_original - backorder_2 - backorder_1
        self.assertEqual(backorder_3.backorder_id.id, backorder_2.id)
        self.assertEqual(line_ids.qty_transferred, 3)

        qty_to_process = {
            self.component_a: 10,
            self.component_b: 1,
            self.component_c: 21,
        }
        self._process_quantities(backorder_3.move_ids, qty_to_process)

        backorder_3.button_validate()
        line_ids._compute_qty_transferred()

        self.assertEqual(line_ids.qty_transferred, 10)

    def test_kit_qty_to_transfer_recomputed(self) -> None:
        stock_location = self.company_data["default_warehouse"].lot_stock_id
        self.env["stock.quant"]._update_available_quantity(
            self.component_a, stock_location, 20
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_b, stock_location, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_c, stock_location, 30
        )

        partner = self.env["res.partner"].create(
            {"name": "Kit qty_to_transfer Partner"}
        )
        f = Form(self.env["sale.order"])
        f.partner_id = partner
        with f.line_ids.new() as line:
            line.product_id = self.kit_1
            line.product_qty = 10.0
        so = f.save()
        so.action_confirm()

        line = so.line_ids[0]
        self.assertEqual(line.qty_transferred, 0)
        self.assertEqual(
            line.qty_to_transfer,
            max(0.0, line.product_qty - line.qty_transferred),
        )

        picking = so.picking_ids
        self._process_quantities(
            picking.move_ids,
            {
                self.component_a: 20,
                self.component_b: 10,
                self.component_c: 30,
            },
        )
        picking.button_validate()
        line._compute_qty_transferred()

        self.assertEqual(
            line.qty_to_transfer,
            max(0.0, line.product_qty - line.qty_transferred),
        )
        self.assertEqual(line.qty_to_transfer, 0)

    def test_kit_qty_transferred_idempotent(self) -> None:
        stock_location = self.company_data["default_warehouse"].lot_stock_id
        self.env["stock.quant"]._update_available_quantity(
            self.component_a, stock_location, 20
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_b, stock_location, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_c, stock_location, 30
        )

        partner = self.env["res.partner"].create({"name": "Kit idempotency Partner"})
        f = Form(self.env["sale.order"])
        f.partner_id = partner
        with f.line_ids.new() as line:
            line.product_id = self.kit_1
            line.product_qty = 10.0
        so = f.save()
        so.action_confirm()

        picking = so.picking_ids
        self._process_quantities(
            picking.move_ids,
            {
                self.component_a: 20,
                self.component_b: 10,
                self.component_c: 30,
            },
        )
        picking.button_validate()

        line = so.line_ids[0]
        line._compute_qty_transferred()
        first = line.qty_transferred
        self.assertEqual(first, 10)

        for _ in range(3):
            line._compute_qty_transferred()
            self.assertEqual(line.qty_transferred, first)

    def test_04_sale_mrp_kit_qty_transferred(self):

        stock_location = self.company_data["default_warehouse"].lot_stock_id
        self.env["stock.quant"]._update_available_quantity(
            self.component_a, stock_location, 56
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_b, stock_location, 28
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_c, stock_location, 84
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_d, stock_location, 14
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_e, stock_location, 7
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_f, stock_location, 14
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_g, stock_location, 28
        )

        partner = self.env["res.partner"].create({"name": "My Test Partner"})
        f = Form(self.env["sale.order"])
        f.partner_id = partner
        with f.line_ids.new() as line:
            line.product_id = self.kit_parent
            line.product_qty = 7.0

        so = f.save()
        so.action_confirm()

        self.assertEqual(len(so.picking_ids), 1)
        line_ids = so.line_ids[0]
        picking_original = so.picking_ids[0]
        move_ids = picking_original.move_ids
        products = move_ids.product_id
        kits = [self.kit_parent, self.kit_3, self.kit_2, self.kit_1]
        components = [
            self.component_a,
            self.component_b,
            self.component_c,
            self.component_d,
            self.component_e,
            self.component_f,
            self.component_g,
        ]
        expected_quantities = {
            self.component_a: 56.0,
            self.component_b: 28.0,
            self.component_c: 84.0,
            self.component_d: 14.0,
            self.component_e: 7.0,
            self.component_f: 14.0,
            self.component_g: 28.0,
        }

        self.assertEqual(len(move_ids), 7)
        self.assertTrue(not any(kit in products for kit in kits))
        self.assertTrue(all(component in products for component in components))
        self._assert_quantities(move_ids, expected_quantities)

        qty_to_process = 7
        move_ids.write({"quantity": qty_to_process, "picked": True})

        Form.from_action(self.env, picking_original.button_validate()).save().process()

        self.assertEqual(len(so.picking_ids), 2)
        backorder_1 = so.picking_ids - picking_original
        self.assertEqual(backorder_1.backorder_id.id, picking_original.id)

        self.assertEqual(line_ids.qty_transferred, 0)

        qty_to_process = {
            self.component_a: 1,
            self.component_c: 5,
        }
        self._process_quantities(backorder_1.move_ids, qty_to_process)

        Form.from_action(self.env, backorder_1.button_validate()).save().process()

        self.assertEqual(line_ids.qty_transferred, 1)

        self.assertEqual(len(so.picking_ids), 3)
        backorder_2 = so.picking_ids - picking_original - backorder_1
        self.assertEqual(backorder_2.backorder_id.id, backorder_1.id)

        expected_quantities = {
            self.component_a: 48,
            self.component_b: 21,
            self.component_c: 72,
            self.component_d: 7,
            self.component_f: 7,
            self.component_g: 21,
        }

        self.assertEqual(len(backorder_2.move_ids), 6)
        move_comp_e = backorder_2.move_ids.filtered(
            lambda m: m.product_id.id == self.component_e.id
        )
        self.assertFalse(move_comp_e)
        self._assert_quantities(backorder_2.move_ids, expected_quantities)

        qty_to_process = {
            self.component_a: 16,
            self.component_b: 5,
            self.component_c: 24,
            self.component_g: 5,
        }
        self._process_quantities(backorder_2.move_ids, qty_to_process)

        Form.from_action(self.env, backorder_2.button_validate()).save().process()

        self.assertEqual(line_ids.qty_transferred, 3)

        self.assertEqual(len(so.picking_ids), 4)
        backorder_3 = so.picking_ids - (picking_original + backorder_1 + backorder_2)
        self.assertEqual(backorder_3.backorder_id.id, backorder_2.id)

        expected_quantities = {
            self.component_a: 32,
            self.component_b: 16,
            self.component_c: 48,
            self.component_d: 7,
            self.component_f: 7,
            self.component_g: 16,
        }
        self._assert_quantities(backorder_3.move_ids, expected_quantities)

        self._process_quantities(backorder_3.move_ids, expected_quantities)

        backorder_3.button_validate()
        self.assertEqual(line_ids.qty_transferred, 7.0)

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=backorder_3.ids,
                active_id=backorder_3.ids[0],
                active_model="stock.picking",
            )
        )
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write(
                {
                    "quantity": expected_quantities[return_move.product_id],
                    "to_refund": True,
                }
            )
        res = return_wiz.action_create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])

        return_pick.button_validate()

        self.assertEqual(line_ids.qty_transferred, 3)

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=return_pick.ids,
                active_id=return_pick.ids[0],
                active_model="stock.picking",
            )
        )
        return_wiz = stock_return_picking_form.save()
        for move in return_wiz.product_return_moves:
            move.quantity = expected_quantities[move.product_id]
        res = return_wiz.action_create_returns()
        return_of_return_pick = self.env["stock.picking"].browse(res["res_id"])

        for move in return_of_return_pick.move_ids:
            move.write(
                {
                    "quantity": expected_quantities[move.product_id] - 1,
                    "picked": True,
                    "to_refund": True,
                }
            )

        Form.from_action(
            self.env, return_of_return_pick.button_validate()
        ).save().process()

        self.assertEqual(line_ids.qty_transferred, 6)

        self.assertEqual(len(so.picking_ids), 7)
        backorder_4 = so.picking_ids - (
            picking_original
            + backorder_1
            + backorder_2
            + backorder_3
            + return_of_return_pick
            + return_pick
        )
        self.assertEqual(backorder_4.backorder_id.id, return_of_return_pick.id)

        for move in backorder_4.move_ids:
            self.assertEqual(move.product_qty, 1)

    @mute_logger("odoo.tests.form.onchange")
    def test_05_mrp_sale_kit_availability(self):
        warehouse_1 = self.env["stock.warehouse"].create(
            {"name": "Warehouse 1", "code": "WH1"}
        )
        warehouse_2 = self.env["stock.warehouse"].create(
            {"name": "Warehouse 2", "code": "WH2"}
        )

        components = [
            self.component_a,
            self.component_b,
            self.component_c,
            self.component_d,
            self.component_e,
            self.component_f,
            self.component_g,
        ]

        self.env["stock.quant"]._update_available_quantity(
            self.component_a, warehouse_1.lot_stock_id, 8
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_b, warehouse_1.lot_stock_id, 4
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_c, warehouse_1.lot_stock_id, 12
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_d, warehouse_1.lot_stock_id, 2
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_e, warehouse_1.lot_stock_id, 1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_f, warehouse_1.lot_stock_id, 2
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_g, warehouse_1.lot_stock_id, 4
        )

        self.env["stock.quant"]._update_available_quantity(
            self.component_a, warehouse_2.lot_stock_id, 7
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_b, warehouse_2.lot_stock_id, 3
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_c, warehouse_2.lot_stock_id, 12
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_d, warehouse_2.lot_stock_id, 1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_e, warehouse_2.lot_stock_id, 1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_f, warehouse_2.lot_stock_id, 1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_g, warehouse_2.lot_stock_id, 4
        )

        qty_ordered = 7
        f = Form(self.env["sale.order"])
        f.partner_id = self.env["res.partner"].create({"name": "My Test Partner"})
        f.warehouse_id = warehouse_2
        with f.line_ids.new() as line:
            line.product_id = self.kit_parent
            line.product_qty = qty_ordered
        so = f.save()
        line_ids = so.line_ids[0]

        kit_parent_wh_order = self.kit_parent.with_context(
            warehouse_id=so.warehouse_id.id
        )

        self.assertEqual(kit_parent_wh_order.qty_available_virtual, 0)
        self.env.invalidate_all()
        kit_parent_wh1 = self.kit_parent.with_context(warehouse_id=warehouse_1.id)
        self.assertEqual(kit_parent_wh1.qty_available_virtual, 1)

        self.assertTrue(
            line.product_uom_id.compare(
                line_ids.qty_available_virtual_at_date - line_ids.product_qty, 0
            )
            == -1
        )

        qty_to_process = {
            self.component_a: (17, self.uom_unit),
            self.component_b: (12, self.uom_unit),
            self.component_c: (25, self.uom_unit),
            self.component_d: (5, self.uom_unit),
            self.component_e: (2, self.uom_unit),
            self.component_f: (5, self.uom_unit),
            self.component_g: (8, self.uom_unit),
        }
        self._create_move_quantities(qty_to_process, components, warehouse_2)

        kit_parent_wh_order = self.kit_parent.with_context(
            warehouse_id=so.warehouse_id.id
        )
        self.assertEqual(kit_parent_wh_order.qty_available_virtual, 3)
        self.env.invalidate_all()
        kit_parent_wh1 = self.kit_parent.with_context(warehouse_id=warehouse_1.id)
        self.assertEqual(kit_parent_wh1.qty_available_virtual, 1)

        self.assertTrue(
            line.product_uom_id.compare(
                line_ids.qty_available_virtual_at_date - line_ids.product_qty, 0
            )
            == -1
        )

        qty_to_process = {
            self.component_a: (32, self.uom_unit),
            self.component_b: (16, self.uom_unit),
            self.component_c: (48, self.uom_unit),
            self.component_d: (8, self.uom_unit),
            self.component_e: (4, self.uom_unit),
            self.component_f: (8, self.uom_unit),
            self.component_g: (16, self.uom_unit),
        }
        self._create_move_quantities(qty_to_process, components, warehouse_2)

        kit_parent_wh_order = self.kit_parent.with_context(
            warehouse_id=so.warehouse_id.id
        )
        self.assertEqual(kit_parent_wh_order.qty_available_virtual, 7)

    def test_06_kit_qty_transferred_mixed_uom(self):
        component_uom_unit = self._cls_create_product("Comp Unit", self.uom_unit)
        component_uom_dozen = self._cls_create_product("Comp Dozen", self.uom_dozen)
        component_uom_kg = self._cls_create_product("Comp Kg", self.uom_kg)

        kit_uom_1 = self._cls_create_product("Kit 1", self.uom_unit)

        bom_kit_uom_1 = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit_uom_1.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        BomLine = self.env["mrp.bom.line"]
        BomLine.create(
            {
                "product_id": component_uom_unit.id,
                "product_qty": 2.0,
                "product_uom_id": self.uom_dozen.id,
                "bom_id": bom_kit_uom_1.id,
            }
        )
        BomLine.create(
            {
                "product_id": component_uom_dozen.id,
                "product_qty": 1.0,
                "product_uom_id": self.uom_dozen.id,
                "bom_id": bom_kit_uom_1.id,
            }
        )
        BomLine.create(
            {
                "product_id": component_uom_kg.id,
                "product_qty": 3.0,
                "product_uom_id": self.uom_gm.id,
                "bom_id": bom_kit_uom_1.id,
            }
        )

        stock_location = self.company_data["default_warehouse"].lot_stock_id
        self.env["stock.quant"]._update_available_quantity(
            component_uom_unit, stock_location, 240
        )
        self.env["stock.quant"]._update_available_quantity(
            component_uom_dozen, stock_location, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            component_uom_kg, stock_location, 0.03
        )

        partner = self.env["res.partner"].create({"name": "My Test Partner"})
        f = Form(self.env["sale.order"])
        f.partner_id = partner
        with f.line_ids.new() as line:
            line.product_id = kit_uom_1
            line.product_qty = 10.0

        so = f.save()
        so.action_confirm()

        picking_original = so.picking_ids[0]
        move_ids = picking_original.move_ids
        line_ids = so.line_ids[0]

        for move in move_ids:
            corr_bom_line = bom_kit_uom_1.bom_line_ids.filtered(
                lambda b, move=move: b.product_id.id == move.product_id.id
            )
            computed_qty = move.product_uom_id._get_quantity_in_unit(
                move.product_qty, corr_bom_line.product_uom_id
            )
            self.assertEqual(
                computed_qty, line_ids.product_qty * corr_bom_line.product_qty
            )

        qty_to_process = {
            component_uom_unit: 48,
            component_uom_dozen: 3,
            component_uom_kg: 0.006,
        }
        self._process_quantities(move_ids, qty_to_process)
        Form.from_action(
            self.env, move_ids.picking_id.button_validate()
        ).save().process()

        self.assertEqual(len(so.picking_ids), 2)
        backorder_1 = so.picking_ids - picking_original
        self.assertEqual(backorder_1.backorder_id.id, picking_original.id)

        self.assertEqual(line_ids.qty_transferred, 2)

        qty_to_process = {
            component_uom_unit: 192,
            component_uom_dozen: 7,
            component_uom_kg: 0.024,
        }
        self._process_quantities(backorder_1.move_ids, qty_to_process)

        backorder_1.button_validate()
        line_ids._compute_qty_transferred()
        self.assertEqual(line_ids.qty_transferred, 10)

    @mute_logger("odoo.tests.form.onchange")
    def test_07_kit_availability_mixed_uom(self):
        component_uom_unit = self._cls_create_product("Comp Unit", self.uom_unit)
        component_uom_dozen = self._cls_create_product("Comp Dozen", self.uom_dozen)
        component_uom_kg = self._cls_create_product("Comp Kg", self.uom_kg)
        component_uom_gm = self._cls_create_product("Comp g", self.uom_gm)
        components = [
            component_uom_unit,
            component_uom_dozen,
            component_uom_kg,
            component_uom_gm,
        ]

        kit_uom_1 = self._cls_create_product("Sub Kit 1", self.uom_unit)
        kit_uom_in_kit = self._cls_create_product("Parent Kit", self.uom_unit)

        bom_kit_uom_1 = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit_uom_1.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        BomLine = self.env["mrp.bom.line"]
        BomLine.create(
            {
                "product_id": component_uom_unit.id,
                "product_qty": 2.0,
                "product_uom_id": self.uom_dozen.id,
                "bom_id": bom_kit_uom_1.id,
            }
        )
        BomLine.create(
            {
                "product_id": component_uom_dozen.id,
                "product_qty": 1.0,
                "product_uom_id": self.uom_dozen.id,
                "bom_id": bom_kit_uom_1.id,
            }
        )
        BomLine.create(
            {
                "product_id": component_uom_kg.id,
                "product_qty": 5.0,
                "product_uom_id": self.uom_gm.id,
                "bom_id": bom_kit_uom_1.id,
            }
        )

        bom_kit_uom_in_kit = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit_uom_in_kit.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        BomLine.create(
            {
                "product_id": component_uom_gm.id,
                "product_qty": 3.0,
                "product_uom_id": self.uom_kg.id,
                "bom_id": bom_kit_uom_in_kit.id,
            }
        )
        BomLine.create(
            {
                "product_id": kit_uom_1.id,
                "product_qty": 2.0,
                "product_uom_id": self.uom_dozen.id,
                "bom_id": bom_kit_uom_in_kit.id,
            }
        )

        warehouse_1 = self.env["stock.warehouse"].create(
            {"name": "Warehouse 1", "code": "WH1"}
        )

        self.env["stock.quant"]._update_available_quantity(
            component_uom_unit, warehouse_1.lot_stock_id, 576
        )
        self.env["stock.quant"]._update_available_quantity(
            component_uom_dozen, warehouse_1.lot_stock_id, 24
        )
        self.env["stock.quant"]._update_available_quantity(
            component_uom_kg, warehouse_1.lot_stock_id, 0.12
        )
        self.env["stock.quant"]._update_available_quantity(
            component_uom_gm, warehouse_1.lot_stock_id, 3000
        )

        qty_ordered = 5
        f = Form(self.env["sale.order"])
        f.partner_id = self.env["res.partner"].create({"name": "My Test Partner"})
        f.warehouse_id = warehouse_1
        with f.line_ids.new() as line:
            line.product_id = kit_uom_in_kit
            line.product_qty = qty_ordered

        so = f.save()
        line_ids = so.line_ids[0]

        kit_uom_in_kit.with_context(warehouse_id=warehouse_1.id)._compute_quantities()
        virtual_available_wh_order = kit_uom_in_kit.qty_available_virtual
        self.assertEqual(virtual_available_wh_order, 1)

        self.assertTrue(
            line.product_uom_id.compare(
                line_ids.qty_available_virtual_at_date - line_ids.product_qty, 0
            )
            == -1
        )

        qty_to_process = {
            component_uom_unit: (1152, self.uom_unit),
            component_uom_dozen: (48, self.uom_dozen),
            component_uom_kg: (0.24, self.uom_kg),
            component_uom_gm: (6000, self.uom_gm),
        }
        self._create_move_quantities(qty_to_process, components, warehouse_1)

        self.assertTrue(
            line.product_uom_id.compare(
                line_ids.qty_available_virtual_at_date - line_ids.product_qty, 0
            )
            == -1
        )
        kit_uom_in_kit.with_context(warehouse_id=warehouse_1.id)._compute_quantities()
        virtual_available_wh_order = kit_uom_in_kit.qty_available_virtual
        self.assertEqual(virtual_available_wh_order, 3)

        self._create_move_quantities(qty_to_process, components, warehouse_1)

        kit_uom_in_kit.with_context(warehouse_id=warehouse_1.id)._compute_quantities()
        self.assertEqual(kit_uom_in_kit.qty_available_virtual, 5)

    def test_10_sale_mrp_kits_routes(self):

        stock_shelf_1 = self.env["stock.location"].create(
            {
                "name": "Shelf 1",
                "location_id": self.company_data["default_warehouse"].lot_stock_id.id,
            }
        )
        stock_shelf_2 = self.env["stock.location"].create(
            {
                "name": "Shelf 2",
                "location_id": self.company_data["default_warehouse"].lot_stock_id.id,
            }
        )

        kit_1 = self._cls_create_product("Kit1", self.uom_unit)
        component_shelf1 = self._cls_create_product("Comp Shelf1", self.uom_unit)
        component_shelf2 = self._cls_create_product("Comp Shelf2", self.uom_unit)

        with Form(self.env["mrp.bom"]) as bom:
            bom.product_tmpl_id = kit_1.product_tmpl_id
            bom.product_qty = 1
            bom.product_uom_id = self.uom_unit
            bom.type = "phantom"
            with bom.bom_line_ids.new() as line:
                line.product_id = component_shelf1
                line.product_qty = 3
                line.product_uom_id = self.uom_unit
            with bom.bom_line_ids.new() as line:
                line.product_id = component_shelf2
                line.product_qty = 2
                line.product_uom_id = self.uom_unit

        route_shelf1 = self.env["stock.route"].create(
            {
                "name": "Shelf1 -> Customer",
                "product_selectable": True,
                "rule_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Shelf1 -> Customer",
                            "action": "pull",
                            "picking_type_id": self.company_data[
                                "default_warehouse"
                            ].out_type_id.id,
                            "location_src_id": stock_shelf_1.id,
                            "location_dest_id": self.ref(
                                "stock.stock_location_customers"
                            ),
                        },
                    )
                ],
            }
        )

        route_shelf2 = self.env["stock.route"].create(
            {
                "name": "Shelf2 -> Customer",
                "product_selectable": True,
                "rule_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Shelf2 -> Customer",
                            "action": "pull",
                            "picking_type_id": self.company_data[
                                "default_warehouse"
                            ].out_type_id.id,
                            "location_src_id": stock_shelf_2.id,
                            "location_dest_id": self.ref(
                                "stock.stock_location_customers"
                            ),
                        },
                    )
                ],
            }
        )

        component_shelf1.write({"route_ids": [(4, route_shelf1.id)]})
        component_shelf2.write({"route_ids": [(4, route_shelf2.id)]})

        self.env["stock.quant"]._update_available_quantity(
            component_shelf1, self.company_data["default_warehouse"].lot_stock_id, 15
        )
        self.env["stock.quant"]._update_available_quantity(
            component_shelf2, self.company_data["default_warehouse"].lot_stock_id, 10
        )

        order_form = Form(self.env["sale.order"])
        order_form.partner_id = self.env["res.partner"].create(
            {"name": "My Test Partner"}
        )
        with order_form.line_ids.new() as line:
            line.product_id = kit_1
            line.product_qty = 5
        order = order_form.save()
        order.action_confirm()

        self.assertEqual(len(order.picking_ids), 2)
        self.assertEqual(len(order.picking_ids[0].move_ids), 1)
        self.assertEqual(len(order.picking_ids[1].move_ids), 1)
        moves = order.picking_ids.move_ids
        move_shelf1 = moves.filtered(lambda m: m.product_id == component_shelf1)
        move_shelf2 = moves.filtered(lambda m: m.product_id == component_shelf2)
        self.assertEqual(move_shelf1.location_id.id, stock_shelf_1.id)
        self.assertEqual(
            move_shelf1.location_dest_id.id, self.ref("stock.stock_location_customers")
        )
        self.assertEqual(move_shelf2.location_id.id, stock_shelf_2.id)
        self.assertEqual(
            move_shelf2.location_dest_id.id, self.ref("stock.stock_location_customers")
        )

    def test_11_sale_mrp_explode_kits_uom_quantities(self):

        kit_1 = self._cls_create_product("Kit1", self.uom_unit)
        component_unit = self._cls_create_product("Comp Unit", self.uom_unit)
        component_kg = self._cls_create_product("Comp Kg", self.uom_kg)

        with Form(self.env["mrp.bom"]) as bom:
            bom.product_tmpl_id = kit_1.product_tmpl_id
            bom.product_qty = 2
            bom.product_uom_id = self.uom_dozen
            bom.type = "phantom"
            with bom.bom_line_ids.new() as line:
                line.product_id = component_unit
                line.product_qty = 6
                line.product_uom_id = self.uom_unit
            with bom.bom_line_ids.new() as line:
                line.product_id = component_kg
                line.product_qty = 7
                line.product_uom_id = self.uom_kg

        warehouse_1 = self.env["stock.warehouse"].create(
            {"name": "Warehouse 1", "code": "WH1"}
        )
        self.env["stock.quant"]._update_available_quantity(
            component_unit, warehouse_1.lot_stock_id, 12
        )
        self.env["stock.quant"]._update_available_quantity(
            component_kg, warehouse_1.lot_stock_id, 14
        )

        order_form = Form(self.env["sale.order"])
        order_form.partner_id = self.env["res.partner"].create(
            {"name": "My Test Partner"}
        )
        order_form.warehouse_id = warehouse_1
        with order_form.line_ids.new() as line:
            line.product_id = kit_1
            line.product_qty = 2
        order = order_form.save()
        order.action_confirm()

        self.assertEqual(len(order.picking_ids), 1)
        self.assertEqual(len(order.picking_ids[0].move_ids), 2)

        move_component_unit = order.picking_ids[0].move_ids.filtered(
            lambda m: m.product_id == component_unit
        )
        move_component_kg = order.picking_ids[0].move_ids - move_component_unit
        self.assertEqual(move_component_unit.product_qty, 0.5)
        self.assertEqual(move_component_kg.product_qty, 0.59)

    def test_product_type_service_1(self):
        route_manufacture = self.company_data[
            "default_warehouse"
        ].manufacture_pull_id.route_id.id
        route_mto = self.company_data["default_warehouse"].mto_pull_id.route_id.id
        self.uom_unit = self.env.ref("uom.product_uom_unit")

        finished_product = self.env["product.product"].create(
            {
                "name": "Geyser",
                "is_storable": True,
                "route_ids": [(4, route_mto), (4, route_manufacture)],
            }
        )

        product_raw = self.env["product.product"].create(
            {
                "name": "raw Geyser",
                "type": "service",
            }
        )

        self.env["mrp.bom"].create(
            {
                "product_id": finished_product.id,
                "product_tmpl_id": finished_product.product_tmpl_id.id,
                "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [(5, 0), (0, 0, {"product_id": product_raw.id})],
            }
        )

        sale_form = Form(self.env["sale.order"])
        sale_form.partner_id = self.env["res.partner"].create(
            {"name": "My Test Partner"}
        )
        with sale_form.line_ids.new() as line:
            line.name = finished_product.name
            line.product_id = finished_product
            line.product_qty = 1.0
            line.price_unit = 10.0
        sale_order = sale_form.save()

        sale_order.action_confirm()

        mo = self.env["mrp.production"].search(
            [("product_id", "=", finished_product.id)]
        )

        self.assertTrue(mo, "Manufacturing order created.")

    def test_cancel_flow_1(self):
        route_manufacture = self.company_data[
            "default_warehouse"
        ].manufacture_pull_id.route_id
        route_mto = self.company_data["default_warehouse"].mto_pull_id.route_id
        route_mto.rule_ids.procure_method = "make_to_order"
        self.uom_unit = self.env.ref("uom.product_uom_unit")

        finished_product = self.env["product.product"].create(
            {
                "name": "Geyser",
                "is_storable": True,
                "route_ids": [(4, route_mto.id), (4, route_manufacture.id)],
            }
        )

        product_raw = self.env["product.product"].create(
            {
                "name": "raw Geyser",
                "is_storable": True,
            }
        )

        self.env["mrp.bom"].create(
            {
                "product_id": finished_product.id,
                "product_tmpl_id": finished_product.product_tmpl_id.id,
                "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [(5, 0), (0, 0, {"product_id": product_raw.id})],
            }
        )

        sale_form = Form(self.env["sale.order"])
        sale_form.partner_id = self.env["res.partner"].create(
            {"name": "My Test Partner"}
        )
        with sale_form.line_ids.new() as line:
            line.name = finished_product.name
            line.product_id = finished_product
            line.product_qty = 1.0
            line.price_unit = 10.0
        sale_order = sale_form.save()

        sale_order.action_confirm()

        mo = self.env["mrp.production"].search(
            [("product_id", "=", finished_product.id)]
        )
        delivery = sale_order.picking_ids
        delivery.action_cancel()
        mo.action_cancel()
        copied_delivery = delivery.copy()
        copied_delivery.action_confirm()
        mos = self.env["mrp.production"].search(
            [("product_id", "=", finished_product.id)]
        )
        self.assertEqual(len(mos), 1)
        self.assertEqual(mos.state, "cancel")

    def test_cancel_flow_2(self):
        route_manufacture = self.company_data[
            "default_warehouse"
        ].manufacture_pull_id.route_id
        route_mto = self.company_data["default_warehouse"].mto_pull_id.route_id
        route_mto.rule_ids.procure_method = "make_to_order"
        self.uom_unit = self.env.ref("uom.product_uom_unit")

        finished_product = self.env["product.product"].create(
            {
                "name": "Geyser",
                "is_storable": True,
                "route_ids": [(4, route_mto.id), (4, route_manufacture.id)],
            }
        )

        product_raw = self.env["product.product"].create(
            {
                "name": "raw Geyser",
                "is_storable": True,
            }
        )

        self.env["mrp.bom"].create(
            {
                "product_id": finished_product.id,
                "product_tmpl_id": finished_product.product_tmpl_id.id,
                "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [(5, 0), (0, 0, {"product_id": product_raw.id})],
            }
        )

        sale_form = Form(self.env["sale.order"])
        sale_form.partner_id = self.env["res.partner"].create(
            {"name": "My Test Partner"}
        )
        with sale_form.line_ids.new() as line:
            line.name = finished_product.name
            line.product_id = finished_product
            line.product_qty = 1.0
            line.price_unit = 10.0
        sale_order = sale_form.save()

        sale_order.action_confirm()

        mo = self.env["mrp.production"].search(
            [("product_id", "=", finished_product.id)]
        )
        delivery = sale_order.picking_ids
        mo.action_cancel()
        delivery.action_cancel()
        copied_delivery = delivery.copy()
        copied_delivery.action_confirm()
        mos = self.env["mrp.production"].search(
            [("product_id", "=", finished_product.id)]
        )
        self.assertEqual(len(mos), 1)
        self.assertEqual(mos.state, "cancel")

    def test_13_so_return_kit(self):
        main_kit_product = self.env["product.product"].create(
            {
                "name": "Main Kit",
                "is_storable": True,
            }
        )

        nested_kit_product = self.env["product.product"].create(
            {
                "name": "Nested Kit",
                "is_storable": True,
            }
        )

        product = self.env["product.product"].create(
            {
                "name": "Screw",
                "is_storable": True,
            }
        )

        self.env["mrp.bom"].create(
            {
                "product_id": nested_kit_product.id,
                "product_tmpl_id": nested_kit_product.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [(5, 0), (0, 0, {"product_id": product.id})],
            }
        )

        self.env["mrp.bom"].create(
            {
                "product_id": main_kit_product.id,
                "product_tmpl_id": main_kit_product.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [(5, 0), (0, 0, {"product_id": nested_kit_product.id})],
            }
        )

        order_form = Form(self.env["sale.order"])
        order_form.partner_id = self.env["res.partner"].create({"name": "Test Partner"})
        with order_form.line_ids.new() as line:
            line.product_id = main_kit_product
            line.product_qty = 1
        order = order_form.save()
        order.action_confirm()
        qty_del_not_yet_validated = sum(sol.qty_transferred for sol in order.line_ids)
        self.assertEqual(qty_del_not_yet_validated, 0.0, "No delivery validated yet")

        pick = order.picking_ids
        pick.move_ids.write({"quantity": 1, "picked": True})
        pick.button_validate()
        qty_del_validated = sum(sol.qty_transferred for sol in order.line_ids)
        self.assertEqual(
            qty_del_validated,
            1.0,
            "The order went from warehouse to client, so it has been delivered",
        )

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=pick.ids, active_id=pick.ids[0], active_model="stock.picking"
            )
        )
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write({"quantity": 1, "to_refund": True})
        res = return_wiz.action_create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])
        return_pick.move_line_ids.quantity = 1
        return_pick.button_validate()

        qty_del_return_validated = sum(sol.qty_transferred for sol in order.line_ids)
        self.assertNotEqual(
            qty_del_return_validated,
            1.0,
            "The return was validated, therefore the delivery from client to"
            " company was successful, and the client is left without his 1 product.",
        )
        self.assertEqual(
            qty_del_return_validated,
            0.0,
            "The return has processed, client doesn't have any quantity anymore",
        )

    def test_14_change_bom_type(self):
        p1 = self._cls_create_product("Master", self.uom_unit)
        p2 = self._cls_create_product("Component", self.uom_unit)
        p3 = self.component_a
        p1.categ_id.write(
            {
                "property_cost_method": "average",
                "property_valuation": "real_time",
            }
        )
        stock_location = self.company_data["default_warehouse"].lot_stock_id
        self.env["stock.quant"]._update_available_quantity(
            self.component_a, stock_location, 1
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": p1.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": p2.id,
                            "product_qty": 1.0,
                        },
                    )
                ],
            }
        )

        p2_bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": p2.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": p3.id,
                            "product_qty": 1.0,
                        },
                    )
                ],
            }
        )

        so_form = Form(self.env["sale.order"])
        so_form.partner_id = self.env["res.partner"].create({"name": "Super Partner"})
        with so_form.line_ids.new() as so_line:
            so_line.product_id = p1
        so = so_form.save()
        so.action_confirm()

        so.picking_ids.button_validate()

        p2_bom.type = "normal"

        so._create_invoices()
        invoice = so.invoice_ids
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")

    def test_15_anglo_saxon_variant_price_unit(self):
        self.env.company.currency_id = self.env.ref("base.USD")
        self.env.company.account_config_id.anglo_saxon_accounting = True
        self.partner = self.env["res.partner"].create({"name": "Test Partner"})
        self.category = self.env.ref("product.product_category_goods").copy(
            {
                "name": "Test category",
                "property_valuation": "real_time",
                "property_cost_method": "fifo",
            }
        )
        self.stock_location = self.company_data["default_warehouse"].lot_stock_id

        self.prod_att_test = self.env["product.attribute"].create({"name": "test"})
        self.prod_attr_KIT = self.env["product.attribute.value"].create(
            {"name": "KIT", "attribute_id": self.prod_att_test.id, "sequence": 1}
        )
        self.prod_attr_NOKIT = self.env["product.attribute.value"].create(
            {"name": "NOKIT", "attribute_id": self.prod_att_test.id, "sequence": 2}
        )

        self.product_template = self.env["product.template"].create(
            {
                "name": "Template A",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
                "invoice_policy": "transferred",
                "categ_id": self.category.id,
                "attribute_line_ids": [
                    (
                        0,
                        0,
                        {
                            "attribute_id": self.prod_att_test.id,
                            "value_ids": [
                                (6, 0, [self.prod_attr_KIT.id, self.prod_attr_NOKIT.id])
                            ],
                        },
                    )
                ],
            }
        )

        self.pt_attr_KIT = self.product_template.attribute_line_ids[
            0
        ].product_template_value_ids[0]
        self.pt_attr_NOKIT = self.product_template.attribute_line_ids[
            0
        ].product_template_value_ids[1]
        self.variant_KIT = self.product_template._get_variant_for_combination(
            self.pt_attr_KIT
        )
        self.variant_NOKIT = self.product_template._get_variant_for_combination(
            self.pt_attr_NOKIT
        )
        self.variant_NOKIT.write({"standard_price": 25})

        self.comp_kit_a = self.env["product.product"].create(
            {
                "name": "Component Kit A",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
                "categ_id": self.category.id,
                "standard_price": 20,
            }
        )
        self.comp_kit_b = self.env["product.product"].create(
            {
                "name": "Component Kit B",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
                "categ_id": self.category.id,
                "standard_price": 10,
            }
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_template.id,
                "product_id": self.variant_KIT.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )
        self.env["mrp.bom.line"].create(
            {"product_id": self.comp_kit_a.id, "product_qty": 2.0, "bom_id": bom.id}
        )
        self.env["mrp.bom.line"].create(
            {"product_id": self.comp_kit_b.id, "product_qty": 1.0, "bom_id": bom.id}
        )

        self.env["stock.quant"]._update_available_quantity(
            self.comp_kit_a, self.stock_location, 2
        )
        self.env["stock.quant"]._update_available_quantity(
            self.comp_kit_b, self.stock_location, 1
        )
        self.env["stock.quant"]._update_available_quantity(
            self.variant_NOKIT, self.stock_location, 1
        )

        so_vals = {
            "partner_id": self.partner.id,
            "partner_invoice_id": self.partner.id,
            "partner_shipping_id": self.partner.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": self.variant_KIT.name,
                        "product_id": self.variant_KIT.id,
                        "product_qty": 1,
                        "price_unit": 100,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": self.variant_NOKIT.name,
                        "product_id": self.variant_NOKIT.id,
                        "product_qty": 1,
                        "price_unit": 50,
                    },
                ),
            ],
            "company_id": self.env.company.id,
        }
        so = self.env["sale.order"].create(so_vals)
        so.action_confirm()
        pick = so.picking_ids
        pick.button_validate()
        so._create_invoices()
        invoice = so.invoice_ids
        invoice.action_post()

        amls = invoice.line_ids
        aml_kit_expense = amls.filtered(
            lambda l: (
                l.display_type == "cogs"
                and l.debit > 0
                and l.product_id == self.variant_KIT
            )
        )
        aml_kit_output = amls.filtered(
            lambda l: (
                l.display_type == "cogs"
                and l.credit > 0
                and l.product_id == self.variant_KIT
            )
        )
        aml_nokit_expense = amls.filtered(
            lambda l: (
                l.display_type == "cogs"
                and l.debit > 0
                and l.product_id == self.variant_NOKIT
            )
        )
        aml_nokit_output = amls.filtered(
            lambda l: (
                l.display_type == "cogs"
                and l.credit > 0
                and l.product_id == self.variant_NOKIT
            )
        )

        self.assertEqual(
            aml_kit_expense.debit,
            50,
            "Cost of Good Sold entry missing or mismatching for variant with kit",
        )
        self.assertEqual(
            aml_kit_output.credit,
            50,
            "Cost of Good Sold entry missing or mismatching for variant with kit",
        )
        self.assertEqual(
            aml_nokit_expense.debit,
            25,
            "Cost of Good Sold entry missing or mismatching for variant without kit",
        )
        self.assertEqual(
            aml_nokit_output.credit,
            25,
            "Cost of Good Sold entry missing or mismatching for variant without kit",
        )

    def test_16_anglo_saxon_variant_price_unit_multi_company(self):
        self.partner = self.env["res.partner"].create({"name": "Test Partner"})
        self.category = self.env.ref("product.product_category_goods").copy(
            {
                "name": "Test category",
                "property_valuation": "real_time",
                "property_cost_method": "fifo",
            }
        )
        account_receiv = self.env["account.account"].create(
            {
                "name": "Receivable",
                "code": "RCV00",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        account_income = self.env["account.account"].create(
            {
                "name": "Income",
                "code": "INC00",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        account_expense = self.env["account.account"].create(
            {
                "name": "Expense",
                "code": "EXP00",
                "account_type": "liability_current",
                "reconcile": True,
            }
        )
        account_valuation = self.env["account.account"].create(
            {
                "name": "Valuation",
                "code": "STV00",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        self.stock_location = self.company_data["default_warehouse"].lot_stock_id
        self.partner.property_account_receivable_id = account_receiv
        self.category.property_account_income_categ_id = account_income
        self.category.property_account_expense_categ_id = account_expense
        self.category.property_stock_valuation_account_id = account_valuation

        self.prod_att_test = self.env["product.attribute"].create({"name": "test"})
        self.prod_attr_KIT_A = self.env["product.attribute.value"].create(
            {"name": "KIT A", "attribute_id": self.prod_att_test.id, "sequence": 1}
        )

        self.product_template = self.env["product.template"].create(
            {
                "name": "Template A",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
                "invoice_policy": "transferred",
                "categ_id": self.category.id,
                "attribute_line_ids": [
                    (
                        0,
                        0,
                        {
                            "attribute_id": self.prod_att_test.id,
                            "value_ids": [(6, 0, [self.prod_attr_KIT_A.id])],
                        },
                    )
                ],
            }
        )

        self.pt_attr_KIT_A = self.product_template.attribute_line_ids[
            0
        ].product_template_value_ids[0]
        self.variant_KIT_A = self.product_template._get_variant_for_combination(
            self.pt_attr_KIT_A
        )
        self.variant_KIT_A.write({"standard_price": 25})

        self.comp_kit_a = self.env["product.product"].create(
            {
                "name": "Component Kit A",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
                "categ_id": self.category.id,
                "standard_price": 20,
            }
        )
        self.comp_kit_b = self.env["product.product"].create(
            {
                "name": "Component Kit B",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
                "categ_id": self.category.id,
                "standard_price": 10,
            }
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_template.id,
                "product_id": self.variant_KIT_A.id,
                "product_qty": 1.0,
                "type": "phantom",
                "company_id": self.env.company.id,
            }
        )
        self.env["mrp.bom.line"].create(
            {
                "product_id": self.comp_kit_a.id,
                "product_qty": 1.0,
                "company_id": self.env.company.id,
                "bom_id": bom.id,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            self.comp_kit_a, self.stock_location, 2
        )
        self.env["stock.quant"]._update_available_quantity(
            self.comp_kit_b, self.stock_location, 1
        )

        so_vals = {
            "partner_id": self.partner.id,
            "partner_invoice_id": self.partner.id,
            "partner_shipping_id": self.partner.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": self.variant_KIT_A.name,
                        "product_id": self.variant_KIT_A.id,
                        "product_qty": 1,
                        "price_unit": 50,
                    },
                )
            ],
            "company_id": self.env.company.id,
        }
        so = self.env["sale.order"].create(so_vals)
        so.action_confirm()
        pick = so.picking_ids
        pick.button_validate()
        bom_updated = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_template.id,
                "product_id": self.variant_KIT_A.id,
                "product_qty": 1.0,
                "type": "phantom",
                "company_id": self.env.company.id,
            }
        )
        self.env["mrp.bom.line"].create(
            {
                "product_id": self.comp_kit_b.id,
                "product_qty": 1.0,
                "company_id": self.env.company.id,
                "bom_id": bom_updated.id,
            }
        )

        so._create_invoices()
        invoice = so.invoice_ids
        invoice.action_post()

        amls = invoice.line_ids
        aml_nokit_expense = amls.filtered(
            lambda l: (
                l.display_type == "cogs"
                and l.debit > 0
                and l.product_id == self.variant_KIT_A
            )
        )
        aml_nokit_output = amls.filtered(
            lambda l: (
                l.display_type == "cogs"
                and l.credit > 0
                and l.product_id == self.variant_KIT_A
            )
        )

        self.assertEqual(
            aml_nokit_expense.debit,
            20,
            "Cost of Good Sold entry missing or mismatching for variant without kit",
        )
        self.assertEqual(
            aml_nokit_output.credit,
            20,
            "Cost of Good Sold entry missing or mismatching for variant without kit",
        )

    def test_reconfirm_cancelled_kit(self):
        so = self.env["sale.order"].create(
            {
                "partner_id": self.env["res.partner"]
                .create({"name": "Test Partner"})
                .id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.kit_1.name,
                            "product_id": self.kit_1.id,
                            "product_qty": 1.0,
                            "price_unit": 1.0,
                        },
                    )
                ],
            }
        )

        stock_location = self.company_data["default_warehouse"].lot_stock_id
        self.env["stock.quant"]._update_available_quantity(
            self.component_a, stock_location, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_b, stock_location, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_c, stock_location, 10
        )

        so.action_confirm()
        self.assertEqual(
            len(so.picking_ids),
            1,
            "A picking should be created after the SO validation",
        )

        so.picking_ids.button_validate()

        so._action_cancel()
        so.action_draft()
        so.action_confirm()
        self.assertEqual(
            len(so.picking_ids),
            1,
            "The product was already delivered, no need to re-create a delivery order",
        )

    def test_kit_margin_and_return_picking(self):
        kit = self._cls_create_product("Super Kit", self.uom_unit)
        (kit + self.component_a).categ_id.property_cost_method = "fifo"

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.component_a.id,
                            "product_qty": 1.0,
                        },
                    )
                ],
            }
        )

        self.component_a.standard_price = 10
        kit.button_bom_cost()

        stock_location = self.company_data["default_warehouse"].lot_stock_id
        self.env["stock.quant"]._update_available_quantity(
            self.component_a, stock_location, 1
        )

        so_form = Form(self.env["sale.order"])
        so_form.partner_id = self.partner_a
        with so_form.line_ids.new() as line:
            line.product_id = kit
        so = so_form.save()
        so.action_confirm()

        self.assertEqual(kit.standard_price, 10)

        picking = so.picking_ids
        picking.button_validate()

        ctx = {
            "active_ids": picking.ids,
            "active_id": picking.ids[0],
            "active_model": "stock.picking",
        }
        return_picking_wizard_form = Form(
            self.env["stock.return.picking"].with_context(ctx)
        )
        return_picking_wizard = return_picking_wizard_form.save()
        return_picking_wizard.product_return_moves.quantity = 1
        return_picking_wizard.action_create_returns()

        kit.button_bom_cost()
        self.assertEqual(kit.standard_price, 10)

    def test_kit_decrease_sol_qty(self):
        stock_location = self.company_data["default_warehouse"].lot_stock_id
        custo_location = self.env.ref("stock.stock_location_customers")

        grp_uom = self.env.ref("uom.group_uom")
        self.env.user.write({"group_ids": [(4, grp_uom.id)]})

        self.env["stock.quant"]._update_available_quantity(
            self.component_f, stock_location, 100
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_g, stock_location, 200
        )

        so_form = Form(self.env["sale.order"])
        so_form.partner_id = self.partner_a
        with so_form.line_ids.new() as line:
            line.product_id = self.kit_3
            line.product_qty = 7
            line.product_uom_id = self.uom_ten
        so = so_form.save()
        so.action_confirm()

        delivery = so.picking_ids
        self.assertRecordValues(
            delivery.move_ids,
            [
                {"product_id": self.component_f.id, "product_qty": 70},
                {"product_id": self.component_g.id, "product_qty": 140},
            ],
        )

        with Form(so) as so_form:
            with so_form.line_ids.edit(0) as line:
                line.product_qty = 6
        self.assertRecordValues(
            delivery.move_ids,
            [
                {"product_id": self.component_f.id, "product_qty": 60},
                {"product_id": self.component_g.id, "product_qty": 120},
            ],
        )

        with Form(so) as so_form:
            with so_form.line_ids.edit(0) as line:
                line.product_qty = 10
        self.assertRecordValues(
            delivery.move_ids,
            [
                {"product_id": self.component_f.id, "product_qty": 100},
                {"product_id": self.component_g.id, "product_qty": 200},
            ],
        )
        delivery.button_validate()

        return_wizard_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=delivery.ids,
                active_id=delivery.id,
                active_model="stock.picking",
            )
        )
        return_wizard = return_wizard_form.save()
        return_wizard.product_return_moves[0].quantity = 20
        return_wizard.product_return_moves[1].quantity = 40
        action = return_wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(action["res_id"])
        return_picking.move_ids.picked = True
        return_picking.button_validate()

        with Form(so) as so_form:
            with so_form.line_ids.edit(0) as line:
                line.product_qty = 8

        self.assertRecordValues(
            so.picking_ids.sorted("id").move_ids,
            [
                {
                    "product_id": self.component_f.id,
                    "location_dest_id": custo_location.id,
                    "quantity": 100,
                    "state": "done",
                },
                {
                    "product_id": self.component_g.id,
                    "location_dest_id": custo_location.id,
                    "quantity": 200,
                    "state": "done",
                },
                {
                    "product_id": self.component_f.id,
                    "location_dest_id": stock_location.id,
                    "quantity": 20,
                    "state": "done",
                },
                {
                    "product_id": self.component_g.id,
                    "location_dest_id": stock_location.id,
                    "quantity": 40,
                    "state": "done",
                },
            ],
        )

    def test_kit_decrease_sol_qty_to_zero(self):
        stock_location = self.company_data["default_warehouse"].lot_stock_id

        grp_uom = self.env.ref("uom.group_uom")
        self.env.user.write({"group_ids": [(4, grp_uom.id)]})

        self.env["stock.quant"]._update_available_quantity(
            self.component_f, stock_location, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_g, stock_location, 20
        )

        so_form = Form(self.env["sale.order"])
        so_form.partner_id = self.partner_a
        with so_form.line_ids.new() as line:
            line.product_id = self.kit_3
            line.product_qty = 2
            line.product_uom_id = self.uom_ten
        so = so_form.save()
        so.action_confirm()

        delivery = so.picking_ids
        self.assertRecordValues(
            delivery.move_ids,
            [
                {"product_id": self.component_f.id, "product_qty": 20},
                {"product_id": self.component_g.id, "product_qty": 40},
            ],
        )

        with Form(so) as so_form:
            with so_form.line_ids.edit(0) as line:
                line.product_qty = 0
        self.assertRecordValues(
            delivery.move_ids,
            [
                {"product_id": self.component_f.id, "product_qty": 0},
                {"product_id": self.component_g.id, "product_qty": 0},
            ],
        )

    def test_kit_return_and_decrease_sol_qty_to_zero(self):
        stock_location = self.company_data["default_warehouse"].lot_stock_id
        self.company_data["default_warehouse"].delivery_steps = "pick_ship"

        grp_uom = self.env.ref("uom.group_uom")
        self.env.user.write({"group_ids": [(4, grp_uom.id)]})

        self.env["stock.quant"]._update_available_quantity(
            self.component_f, stock_location, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_g, stock_location, 20
        )

        so_form = Form(self.env["sale.order"])
        so_form.partner_id = self.partner_a
        with so_form.line_ids.new() as line:
            line.product_id = self.kit_3
            line.product_qty = 2
            line.product_uom_id = self.uom_ten
        so = so_form.save()
        so.action_confirm()

        pick = so.picking_ids
        for m in pick.move_ids:
            m.write({"quantity": m.product_uom_qty, "picked": True})
        pick.button_validate()
        self.assertEqual(pick.state, "done")
        delivery = so.picking_ids - pick
        for m in delivery.move_ids:
            m.write({"quantity": m.product_qty, "picked": True})
        delivery.button_validate()
        self.assertEqual(delivery.state, "done")
        self.assertEqual(so.line_ids.qty_transferred, 2)

        ctx = {"active_id": delivery.id, "active_model": "stock.picking"}
        return_wizard = Form(self.env["stock.return.picking"].with_context(ctx)).save()
        for line in return_wizard.product_return_moves:
            line.quantity = line.move_id.quantity
        return_picking = return_wizard._create_return()
        for m in return_picking.move_ids:
            m.write({"quantity": m.product_qty, "picked": True})
        return_picking.button_validate()

        self.assertEqual(return_picking.state, "done")
        self.assertEqual(so.line_ids.qty_transferred, 0)

        with Form(so) as so_form:
            with so_form.line_ids.edit(0) as line:
                line.product_qty = 0

        self.assertEqual(so.picking_ids, pick | delivery | return_picking)
        self.assertRecordValues(
            so.picking_ids.move_ids.sorted(
                lambda m: (m.picking_id.id, m.product_id.id)
            ),
            [
                {
                    "picking_id": pick.id,
                    "product_id": self.component_f.id,
                    "quantity": 20.0,
                },
                {
                    "picking_id": pick.id,
                    "product_id": self.component_g.id,
                    "quantity": 40.0,
                },
                {
                    "picking_id": delivery.id,
                    "product_id": self.component_f.id,
                    "quantity": 20.0,
                },
                {
                    "picking_id": delivery.id,
                    "product_id": self.component_g.id,
                    "quantity": 40.0,
                },
                {
                    "picking_id": return_picking.id,
                    "product_id": self.component_f.id,
                    "quantity": 20.0,
                },
                {
                    "picking_id": return_picking.id,
                    "product_id": self.component_g.id,
                    "quantity": 40.0,
                },
            ],
        )

    def test_fifo_reverse_and_create_new_invoice(self):
        kit = self._cls_create_product("Simple Kit", self.uom_unit)
        categ_form = Form(self.env["product.category"])
        categ_form.name = "Super Fifo"
        categ_form.property_cost_method = "fifo"
        categ_form.property_valuation = "real_time"
        categ = categ_form.save()
        (kit + self.component_a).categ_id = categ

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": self.component_a.id, "product_qty": 1.0})
                ],
            }
        )

        in_moves = self.env["stock.move"].create(
            [
                {
                    "product_id": self.component_a.id,
                    "location_id": self.env.ref("stock.stock_location_suppliers").id,
                    "location_dest_id": self.company_data[
                        "default_warehouse"
                    ].lot_stock_id.id,
                    "product_uom_id": self.component_a.uom_id.id,
                    "product_uom_qty": 1,
                    "price_unit": p,
                    "value_manual": p,
                }
                for p in [10, 50]
            ]
        )
        in_moves._action_confirm()
        in_moves.write({"quantity": 1, "picked": True})
        in_moves._action_done()

        so = self.env["sale.order"].create(
            {
                "partner_id": self.env["res.partner"]
                .create({"name": "Test Partner"})
                .id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": kit.name,
                            "product_id": kit.id,
                            "product_qty": 1.0,
                            "price_unit": 100,
                            "tax_ids": False,
                        },
                    )
                ],
            }
        )
        so.action_confirm()

        picking = so.picking_ids
        picking.move_ids.write({"quantity": 1.0, "picked": True})
        picking.button_validate()

        invoice01 = so._create_invoices()
        invoice01.action_post()

        move_reversal = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=invoice01.ids)
            .create(
                {
                    "journal_id": invoice01.journal_id.id,
                }
            )
        )
        reversal = move_reversal.modify_moves()
        invoice02 = self.env["account.move"].browse(reversal["res_id"])
        invoice02.action_post()

        cogs_amls = invoice02.line_ids.filtered(lambda aml: aml.display_type == "cogs")
        stock_out_aml = cogs_amls.filtered(lambda aml: aml.credit)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 10)
        cogs_aml = cogs_amls.filtered(lambda aml: aml.debit)
        self.assertEqual(cogs_aml.debit, 10)
        self.assertEqual(cogs_aml.credit, 0)

    def test_avoid_removing_kit_bom_in_use(self):
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.kit_1.name,
                            "product_id": self.kit_1.id,
                            "product_qty": 1.0,
                            "price_unit": 5,
                            "tax_ids": False,
                        },
                    )
                ],
            }
        )
        self.bom_kit_1.action_archive()
        self.bom_kit_1.action_unarchive()

        so.action_confirm()
        with self.assertRaises(UserError):
            self.bom_kit_1.write({"type": "normal"})
        with self.assertRaises(UserError):
            self.bom_kit_1.action_archive()
        with self.assertRaises(UserError):
            self.bom_kit_1.unlink()

        for move in so.line_ids.move_ids:
            move.write({"quantity": move.product_qty, "picked": True})
        so.picking_ids.button_validate()

        self.assertEqual(so.picking_ids.state, "done")
        with self.assertRaises(UserError):
            self.bom_kit_1.write({"type": "normal"})
        with self.assertRaises(UserError):
            self.bom_kit_1.action_archive()
        with self.assertRaises(UserError):
            self.bom_kit_1.unlink()

        invoice = so._create_invoices()
        invoice.action_post()

        self.assertEqual(invoice.state, "posted")
        self.bom_kit_1.action_archive()
        self.bom_kit_1.action_unarchive()
        self.bom_kit_1.write({"type": "normal"})
        self.bom_kit_1.write({"type": "phantom"})
        self.bom_kit_1.unlink()

    def test_merge_move_kit_on_adding_new_sol(self):
        warehouse = self.company_data["default_warehouse"]
        warehouse.delivery_steps = "pick_ship"
        kit = self.kit_3
        bom_copy = kit.bom_ids[0].copy()
        kit_copy = kit.copy()
        bom_copy.product_tmpl_id = kit_copy.product_tmpl_id
        self.env["stock.quant"]._update_available_quantity(
            self.component_f, warehouse.lot_stock_id, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_g, warehouse.lot_stock_id, 20
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_a, warehouse.lot_stock_id, 5
        )

        so_form = Form(self.env["sale.order"])
        so_form.partner_id = self.partner_a
        with so_form.line_ids.new() as line:
            line.product_id = kit
            line.product_qty = 2
        with so_form.line_ids.new() as line:
            line.product_id = kit_copy
            line.product_qty = 3
        so = so_form.save()
        so.action_confirm()

        pick = so.picking_ids.filtered(
            lambda p: p.picking_type_id == warehouse.pick_type_id
        )
        expected_pick_moves = [
            {
                "quantity": 2.0,
                "product_id": self.component_f.id,
                "bom_line_id": kit.bom_ids[0]
                .bom_line_ids.filtered(lambda bl: bl.product_id == self.component_f)
                .id,
            },
            {
                "quantity": 3.0,
                "product_id": self.component_f.id,
                "bom_line_id": bom_copy.bom_line_ids.filtered(
                    lambda bl: bl.product_id == self.component_f
                ).id,
            },
            {
                "quantity": 4.0,
                "product_id": self.component_g.id,
                "bom_line_id": kit.bom_ids[0]
                .bom_line_ids.filtered(lambda bl: bl.product_id == self.component_g)
                .id,
            },
            {
                "quantity": 6.0,
                "product_id": self.component_g.id,
                "bom_line_id": bom_copy.bom_line_ids.filtered(
                    lambda bl: bl.product_id == self.component_g
                ).id,
            },
        ]
        self.assertRecordValues(
            pick.move_ids.sorted(lambda m: m.quantity), expected_pick_moves
        )
        with Form(so) as so_form:
            with so_form.line_ids.new() as line:
                line.product_id = self.component_a
                line.product_qty = 1
        expected_pick_moves = [
            {"quantity": 1.0, "product_id": self.component_a.id, "bom_line_id": False},
        ] + expected_pick_moves
        self.assertRecordValues(
            pick.move_ids.sorted(lambda m: m.quantity), expected_pick_moves
        )

    def test_return_kit_in_quarantine_location(self):
        wh = self.company_data["default_warehouse"]
        stock_location = wh.lot_stock_id

        return_location = self.env["stock.location"].create(
            {
                "location_id": stock_location.location_id.id,
                "name": "Return Location",
                "usage": "internal",
            }
        )

        self.env["stock.route"].create(
            {
                "name": "Return Route",
                "warehouse_selectable": True,
                "warehouse_ids": [(4, wh.id)],
                "rule_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Return to Stock",
                            "location_src_id": return_location.id,
                            "location_dest_id": stock_location.id,
                            "company_id": self.company_data["company"].id,
                            "action": "push",
                            "auto": "manual",
                            "picking_type_id": wh.int_type_id.id,
                        },
                    )
                ],
            }
        )

        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (0, 0, {"product_id": self.kit_1.id}),
                ],
            }
        )
        order.action_confirm()

        delivery = order.picking_ids
        for move in delivery.move_ids:
            move.quantity = move.product_qty
        delivery.button_validate()
        self.assertEqual(delivery.state, "done")

        return_wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=delivery.id, active_model="stock.picking")
            .create({})
        )
        for line in return_wizard.product_return_moves:
            line.quantity = line.move_quantity
        res = return_wizard.action_create_returns()

        return_picking = self.env["stock.picking"].browse(res["res_id"])
        return_picking.location_dest_id = return_location
        for move in return_picking.move_ids:
            move.quantity = move.product_qty
        return_picking.button_validate()
        self.assertEqual(return_picking.state, "done")
        self.assertEqual(order.line_ids.qty_transferred, 0)

        internal_picking = return_picking.move_ids.move_dest_ids.picking_id
        self.assertTrue(internal_picking)

        for move in internal_picking.move_ids:
            move.quantity = move.product_qty
        internal_picking.button_validate()
        self.assertEqual(internal_picking.state, "done")
        self.assertEqual(order.line_ids.qty_transferred, 0)

    def test_return_for_exchange_kit_product_component(self):
        for comp in self.bom_kit_1.bom_line_ids.product_id:
            self.env["stock.quant"]._update_available_quantity(
                comp, self.company_data["default_warehouse"].lot_stock_id, quantity=10
            )

        comp_to_return = self.bom_kit_1.bom_line_ids.filtered(
            lambda bl: bl.product_qty == 1
        ).product_id
        kit_product = self.kit_1
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": kit_product.id,
                            "product_qty": 1.0,
                        }
                    )
                ],
            }
        )
        sale_order.action_confirm()
        delivery = sale_order.picking_ids
        delivery.action_assign()
        delivery.button_validate()
        return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_id=delivery.id, active_model="stock.picking"
            )
        )
        return_wizard = return_picking_form.save()
        return_wizard.product_return_moves.filtered(
            lambda prm: prm.product_id == comp_to_return
        ).quantity = 1
        res = return_wizard.action_create_exchanges()
        return_picking = self.env["stock.picking"].browse(res["res_id"])
        return_picking.button_validate()
        exchange_picking = sale_order.picking_ids.filtered(
            lambda so: so.state != "done"
        )
        exchange_picking.button_validate()
        self.assertEqual(sale_order.line_ids.qty_transferred, 1)

    def test_bidirectional_so_mo_link_with_mtso(self):
        route_manufacture = self.company_data[
            "default_warehouse"
        ].manufacture_pull_id.route_id
        route_mto = self.company_data["default_warehouse"].mto_pull_id.route_id
        self.product_a.route_ids = [Command.set([route_manufacture.id, route_mto.id])]
        self.env["mrp.bom"].create(
            {"product_tmpl_id": self.product_a.product_tmpl_id.id}
        )
        route_mto.rule_ids.filtered(
            lambda r: r.location_dest_id.usage == "production"
        ).procure_method = "mts_else_mto"
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 1.0,
                        }
                    )
                ],
            }
        )
        sale_order.action_confirm()
        self.assertEqual(sale_order.mrp_production_count, 1)
        mo = sale_order.mrp_production_ids
        self.assertEqual(mo.sale_order_count, 1)

    def test_so_with_kit_and_multiple_same_component(self):
        self.bom_kit_1.bom_line_ids = self.bom_kit_1.bom_line_ids[0]
        self.env["mrp.bom.line"].create(
            [
                {
                    "product_id": self.bom_kit_1.bom_line_ids[0].product_id.id,
                    "product_qty": 1.0,
                    "bom_id": self.bom_kit_1.id,
                },
            ]
        )
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.kit_1.id,
                            "product_qty": 1.0,
                        }
                    )
                ],
            }
        )
        so.action_confirm()

        picking = so.picking_ids
        self.assertEqual(
            len(picking.move_ids),
            2,
            "There should be 2 moves for the same component in the picking",
        )
        self.assertEqual(
            picking.move_ids.product_id,
            self.component_a,
            "All moves should be for the same component",
        )
        self.assertEqual(
            picking.move_ids.bom_line_id,
            self.bom_kit_1.bom_line_ids,
            "Each move should be linked to a BOM line of the kit",
        )

        so._action_cancel()
        self.assertEqual(so.state, "cancel", "The Sale Order should be cancelled")
        self.assertEqual(
            picking.state,
            "cancel",
            "The picking should be cancelled when the Sale Order is cancelled",
        )

        so.action_draft()
        so.action_confirm()

        second_picking = so.picking_ids - picking
        self.assertEqual(
            len(second_picking.move_ids),
            2,
            "The second picking should have 2 moves for the component",
        )
        self.assertEqual(
            second_picking.move_ids.product_id,
            self.component_a,
            "All moves in the second picking should be for the same component",
        )
        self.assertEqual(
            second_picking.move_ids.bom_line_id,
            self.bom_kit_1.bom_line_ids,
            "Each move in the second picking should be linked to a BOM line of the kit",
        )
        self.env["stock.quant"]._update_available_quantity(
            self.component_a,
            self.company_data["default_warehouse"].lot_stock_id,
            quantity=10,
        )
        second_picking.action_assign()
        second_picking.button_validate()
        return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_id=second_picking.id, active_model="stock.picking"
            )
        )
        return_wizard = return_picking_form.save()
        return_wizard.product_return_moves.filtered(
            lambda prm: prm.product_id == self.component_a
        ).quantity = 1
        res = return_wizard.action_create_exchanges()
        return_picking = self.env["stock.picking"].browse(res["res_id"])
        return_picking.button_validate()
        exchange_picking = so.picking_ids.filtered(lambda so: so.state == "assigned")
        exchange_picking.button_validate()
        so.line_ids._compute_qty_transferred()
        self.assertEqual(
            exchange_picking.move_ids.bom_line_id,
            self.bom_kit_1.bom_line_ids[0],
            "All moves in the exchange picking should be linked to the first BOM line.",
        )
        self.assertEqual(exchange_picking.move_ids.quantity, 2)

    def test_delivery_after_splitting_production(self):
        product = self._cls_create_product(
            "Split Product",
            self.uom_unit,
            routes=[
                self.company_data["default_warehouse"].mto_pull_id.route_id,
                self.company_data["default_warehouse"].manufacture_pull_id.route_id,
            ],
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.product_tmpl_id.id,
                "product_uom_id": self.env.ref("uom.product_uom_unit").id,
            }
        )

        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": f"2 of {self.product.name}",
                            "product_id": product.id,
                            "product_qty": 2,
                        }
                    )
                ],
            }
        )
        sale_order.action_confirm()
        sale_picking = sale_order.picking_ids
        self.assertTrue(sale_picking)

        mo = self.env["mrp.production"].search(
            [("product_id", "=", product.id)], limit=1
        )
        action = mo.action_split()
        wizard = Form(self.env[action["res_model"]].with_context(action["context"]))
        wizard.max_batch_size = 1
        wizard.save().action_split()
        self.assertEqual(len(mo.production_group_id.production_ids), 2)

        mo.production_group_id.production_ids[0].button_mark_done()
        self.assertEqual(sale_picking.move_ids.quantity, 1)
        mo.production_group_id.production_ids[1].button_mark_done()
        self.assertEqual(sale_picking.move_ids.quantity, 2)
        sale_picking.button_validate()
        self.assertEqual(sale_order.line_ids.qty_transferred, 2.0)

    def test_mto_manufacture_so_qty_update_merges_finished_moves(self):
        self.env["stock.quant"]._update_available_quantity(
            self.component_a, self.company_data["default_warehouse"].lot_stock_id, 10.0
        )
        product = self.env["product.product"].create(
            {
                "name": "Test MTO Finished",
                "is_storable": True,
                "categ_id": self.stock_account_product_categ.id,
                "route_ids": [
                    Command.set(
                        [
                            self.env.ref("stock.route_warehouse0_mto").id,
                            self.env.ref("mrp.route_warehouse0_manufacture").id,
                        ]
                    )
                ],
            }
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.product_tmpl_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.component_a.id,
                            "product_qty": 1.0,
                        }
                    )
                ],
            }
        )

        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 1.0,
                            "price_unit": 50.0,
                        }
                    )
                ],
            }
        )
        so.action_confirm()

        so.date_commitment = fields.Date.today() + datetime.timedelta(days=1)
        production = so.reference_ids.production_ids
        self.assertEqual(production.date_deadline, so.date_commitment)
        so.line_ids.product_qty = 2.0

        self.assertEqual(len(production), 1)
        self.assertEqual(production.product_qty, 2.0)
        self.assertEqual(
            len(production.move_finished_ids),
            1,
            "Expected a single finished move after qty increase",
        )
        self.assertEqual(
            production.move_finished_ids.date_deadline,
            so.date_commitment,
            "Finished move's deadline should match SO commitment date",
        )
        production.button_mark_done()
        self.assertEqual(production.state, "done")
