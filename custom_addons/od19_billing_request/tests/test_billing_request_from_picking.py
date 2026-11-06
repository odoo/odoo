# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Create a billing request straight from a transfer (Inventory form).

An outgoing delivery maps to an AR request, an incoming receipt to an AP
request. The moves that actually moved are pulled automatically, and a move
already referenced by an active request is never pulled twice.
"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestFromPicking(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The delivery-label module installed in this database requires a DEPT
        # code on pickings, resolved from the current user's employee record.
        cls.department = cls.env["hr.department"].create(
            {"name": "Billing Picking Test", "code": "BPT"}
        )
        cls.env["hr.employee"].create(
            {
                "name": "Billing Picking Test Employee",
                "user_id": cls.env.uid,
                "department_id": cls.department.id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Picking Partner"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Picking Product",
                "type": "consu",
                "is_storable": True,
                "list_price": 30.0,
                "standard_price": 12.0,
            }
        )
        cls.in_type = cls.env.ref("stock.picking_type_in")
        cls.out_type = cls.env.ref("stock.picking_type_out")
        cls.internal_type = cls.env.ref("stock.picking_type_internal")
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.env["stock.quant"].create(
            {
                "product_id": cls.product.id,
                "location_id": cls.stock_location.id,
                "quantity": 50.0,
            }
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _make_picking(self, picking_type, qty=2.0, state="done"):
        picking = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
            }
        )
        self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_qty": qty,
                "product_uom": self.product.uom_id.id,
                "picking_id": picking.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
            }
        )
        picking.move_ids.write({"quantity": qty, "picked": True})
        picking.write({"state": state})
        return picking

    def _request_from(self, picking):
        action = picking.action_od19_create_billing_request()
        request = self.env["od19.billing.request"].browse(action["res_id"])
        return action, request

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_outgoing_picking_creates_ar_request(self):
        picking = self._make_picking(self.out_type, qty=2.0)

        action, request = self._request_from(picking)

        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "od19.billing.request")
        self.assertEqual(request.direction, "ar")
        self.assertEqual(request.origin_ref, picking)
        self.assertEqual(request.origin_model, "stock.picking")
        self.assertEqual(request.partner_id, self.partner)
        self.assertEqual(len(request.line_ids), 1)
        self.assertEqual(request.line_ids.stock_move_id, picking.move_ids)
        self.assertAlmostEqual(request.line_ids.quantity, 2.0)

    def test_incoming_picking_creates_ap_request(self):
        picking = self._make_picking(self.in_type, qty=5.0)

        _action, request = self._request_from(picking)

        self.assertEqual(request.direction, "ap")
        self.assertEqual(request.partner_id, self.partner)
        self.assertEqual(len(request.line_ids), 1)
        self.assertAlmostEqual(request.line_ids.quantity, 5.0)

    def test_non_transfer_picking_is_rejected(self):
        picking = self._make_picking(self.internal_type)

        with self.assertRaises(UserError):
            picking.action_od19_create_billing_request()

    def test_unconfirmed_picking_is_rejected(self):
        picking = self._make_picking(self.out_type, state="assigned")

        with self.assertRaises(UserError):
            picking.action_od19_create_billing_request()

    def test_move_already_requested_is_not_pulled_twice(self):
        picking = self._make_picking(self.out_type, qty=3.0)

        _action, first = self._request_from(picking)
        self.assertEqual(len(first.line_ids), 1)

        _action, second = self._request_from(picking)
        self.assertFalse(second.line_ids)

    def test_picking_form_button_view_exists(self):
        self.assertTrue(
            self.env.ref(
                "od19_billing_request.view_picking_form_od19_billing_request"
            )
        )
