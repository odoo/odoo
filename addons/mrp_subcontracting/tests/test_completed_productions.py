from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.mrp_subcontracting.tests import common


@tagged("post_install", "-at_install")
class TestSubcontractingProductionSync(common.TestMrpSubcontractingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].create(
            {"name": "Production Sync Warehouse", "code": "SYN"}
        )

    def _create_receipt(self):
        receipt = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.in_type_id.id,
                "partner_id": self.subcontractor_partner1.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.warehouse.lot_stock_id.id,
                "move_ids": [
                    Command.create(
                        {"product_id": self.finished.id, "product_uom_qty": 36}
                    )
                ],
            }
        )
        receipt.action_confirm()
        return receipt

    def _create_completed_receipt(self):
        receipt = self._create_receipt()
        move = receipt.move_ids
        production = move._get_subcontract_production()
        productions = production._split_productions({production: [12, 2, 22]})
        for production in productions:
            production.qty_producing = production.product_qty
        for component_move in productions.move_raw_ids:
            component_move.quantity = component_move.product_uom_qty
            component_move.picked = True
        productions.with_context(skip_consumption=True).button_mark_done()
        self.assertEqual(set(productions.mapped("state")), {"done"})
        self.assertEqual(move._get_subcontract_production(), productions)
        return receipt, productions

    def test_reserve_multiple_completed_productions(self):
        receipt, productions = self._create_completed_receipt()
        move = receipt.move_ids
        production_fields = ["state", "product_qty", "qty_producing", "write_date"]
        stock_moves = productions.move_raw_ids | productions.move_finished_ids
        stock_fields = ["state", "quantity", "product_uom_qty", "write_date"]
        before_productions = productions.read(production_fields)
        before_moves = stock_moves.read(stock_fields)
        # Recreate the reservation that raised Expected singleton, including
        # unlink/create callbacks and a second availability check.
        move.move_line_ids.unlink()
        receipt.action_assign()
        receipt.action_assign()

        self.assertEqual(move.quantity, 36)
        self.assertEqual(move.state, "assigned")
        self.assertEqual(move._get_subcontract_production(), productions)
        self.assertEqual(productions.read(production_fields), before_productions)
        self.assertEqual(stock_moves.read(stock_fields), before_moves)

    def test_partial_receipts_do_not_duplicate_completed_production(self):
        receipt, productions = self._create_completed_receipt()
        for quantity in (2, 12, 22):
            receipt.move_ids.quantity = quantity
            receipt.move_ids.picked = True
            action = receipt.button_validate()
            if isinstance(action, dict):
                Form.from_action(self.env, action).save().process()
            self.assertEqual(receipt.state, "done")
            self.assertEqual(receipt.move_ids.quantity, quantity)
            self.assertEqual(
                receipt.move_ids._get_subcontract_production(), productions
            )
            if quantity != 22:
                receipt = receipt.backorder_ids
                self.assertEqual(len(receipt), 1)
                receipt.action_assign()

        self.assertEqual(productions.mapped("product_qty"), [12, 2, 22])
        self.assertEqual(set(productions.mapped("state")), {"done"})
        self.assertEqual(
            self.env["mrp.production"].search([("bom_id", "=", self.bom.id)]),
            productions,
        )
        quant = self.env["stock.quant"]
        self.assertEqual(
            quant._get_available_quantity(self.finished, self.warehouse.lot_stock_id),
            36,
        )
        for component in self.comp1 | self.comp2:
            self.assertEqual(
                quant._get_available_quantity(
                    component,
                    self.subcontractor_partner1.property_stock_subcontractor,
                    allow_negative=True,
                ),
                -36,
            )

    def test_open_production_still_tracks_receipt_quantity(self):
        receipt = self._create_receipt()
        production = receipt.move_ids._get_subcontract_production()
        receipt.move_ids.quantity = 14
        self.assertEqual(production.product_qty, 14)
        self.assertNotIn(production.state, ("done", "cancel"))
