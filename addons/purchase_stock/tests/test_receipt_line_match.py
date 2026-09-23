from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import PurchaseTestCommon


@tagged("post_install", "-at_install")
class TestReceiptLineMatch(PurchaseTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Match = cls.env["purchase.receipt.line.match"]

    def _match_rows(self, partner=None):
        self.env.flush_all()
        return self.Match.search(
            [("partner_id", "=", (partner or self.vendor).id)],
        )

    def _all_rows(self):
        self.env.flush_all()
        return self.Match.search([])

    def _unlink_moves(self, purchase_order):
        moves = purchase_order.picking_ids.move_ids
        moves.purchase_line_id = False
        return moves

    def test_order_line_half_lists_outstanding_lines(self):
        po = self._create_purchase(self.product, quantity=5.0)
        self._unlink_moves(po)
        order_rows = self._match_rows().filtered("order_line_id")
        self.assertEqual(len(order_rows), 1)
        self.assertEqual(order_rows.order_id, po)
        self.assertEqual(order_rows.line_qty, 5.0)
        self.assertEqual(order_rows.qty_to_transfer, 5.0)
        self.assertFalse(order_rows.move_id)

    def test_move_half_lists_only_unlinked_moves(self):
        po = self._create_purchase(self.product, quantity=5.0)
        self.assertFalse(
            self._match_rows().filtered("move_id"),
            "a move already carrying purchase_line_id must not be offered",
        )
        moves = self._unlink_moves(po)
        move_rows = self._match_rows().filtered("move_id")
        self.assertEqual(len(move_rows), 1)
        self.assertEqual(move_rows.move_id, moves)
        self.assertLess(move_rows.id, 0, "move rows carry the negative id")

    def test_match_links_move_to_line(self):
        po = self._create_purchase(self.product, quantity=5.0)
        move = po.picking_ids.move_ids
        self._unlink_moves(po)
        self._match_rows().action_match_lines()
        self.assertEqual(move.purchase_line_id, po.line_ids)

    def test_assigned_move_over_residual_is_split(self):
        po = self._create_purchase(self.product, quantity=5.0)
        move = po.picking_ids.move_ids
        move.product_uom_qty = 8.0
        self._unlink_moves(po)
        self._match_rows().action_match_lines()
        self.assertEqual(move.purchase_line_id, po.line_ids)
        self.assertEqual(move.product_uom_qty, 5.0, "kept part is the residual")
        siblings = move.picking_id.move_ids - move
        self.assertEqual(len(siblings), 1, "the excess became its own move")
        self.assertEqual(siblings.product_uom_qty, 3.0)
        self.assertFalse(siblings.purchase_line_id, "the excess stays unlinked")

    def test_done_move_over_residual_links_whole_and_over_transfers(self):
        po = self._create_purchase(self.product, quantity=5.0)
        self._receive(po, quantity=8.0)
        move = po.picking_ids.move_ids
        self.assertEqual(move.state, "done")
        self._unlink_moves(po)
        self._match_rows().action_match_lines()
        self.assertEqual(
            move.purchase_line_id,
            po.line_ids,
            "a done move cannot be split, so it is linked whole",
        )
        self.assertEqual(po.line_ids.transfer_state, "over done")

    def test_draft_move_is_never_offered(self):
        po = self._create_purchase(self.product, quantity=5.0, confirm=False)
        draft_move = self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 3.0,
                "product_uom_id": self.product.uom_id.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.env.ref("stock.stock_location_stock").id,
            }
        )
        self.assertEqual(draft_move.state, "draft")
        self.assertNotIn(
            draft_move,
            self._all_rows().move_id,
            "a draft move cannot be split, so it must not be offered at all",
        )
        del po

    def test_scrap_and_inventory_moves_are_excluded(self):
        po = self._create_purchase(self.product, quantity=5.0)
        self._receive(po)
        move = self._unlink_moves(po)
        move.is_inventory = True
        self.assertNotIn(
            move,
            self._all_rows().move_id,
            "an inventory adjustment is not order fulfilment",
        )

    def test_service_lines_are_excluded(self):
        service = self.env["product.product"].create(
            {"name": "consulting", "type": "service"}
        )
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": service.id,
                            "product_qty": 2.0,
                            "product_uom_id": service.uom_id.id,
                            "price_unit": 50.0,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        po.action_confirm()
        self.assertNotIn(
            service,
            self._all_rows().product_id,
            "a service generates no move, so it has nothing to match against",
        )

    def test_no_order_line_selected_raises(self):
        po = self._create_purchase(self.product, quantity=5.0)
        self._unlink_moves(po)
        move_rows = self._match_rows().filtered("move_id")
        with self.assertRaises(UserError):
            move_rows.action_match_lines()
