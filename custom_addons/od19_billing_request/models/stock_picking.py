# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import _, models
from odoo.exceptions import UserError

# ชนิดการโอน -> ทิศทางบิล (ใบส่งของ = AR, ใบรับของ = AP)
_DIRECTION_BY_PICKING_TYPE = {"outgoing": "ar", "incoming": "ap"}

# สถานะคำขอที่ยังถือสิทธิ์บนบรรทัดต้นทาง (ใช้กันการดึงซ้ำ)
_ACTIVE_REQUEST_STATES = ("draft", "submitted", "invoiced")


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _od19_billing_direction(self):
        """คืนทิศทางบิลจากชนิดการโอน หรือ False ถ้าไม่รองรับ."""
        self.ensure_one()
        return _DIRECTION_BY_PICKING_TYPE.get(self.picking_type_code)

    def _od19_billing_pullable_moves(self):
        """งานโอนที่ยังไม่ถูกอ้างอิงในคำขอเปิดบิลที่ยัง active อยู่."""
        self.ensure_one()
        moves = self.move_ids.filtered(
            lambda move: move.product_id and move.quantity > 0
        )
        if not moves:
            return moves
        taken_ids = (
            self.env["od19.billing.request.line"]
            .search(
                [
                    ("origin_line_model", "=", "stock.picking"),
                    ("origin_line_id", "in", moves.ids),
                    ("request_id.state", "in", _ACTIVE_REQUEST_STATES),
                ]
            )
            .mapped("origin_line_id")
        )
        return moves.filtered(lambda move: move.id not in taken_ids)

    def action_od19_create_billing_request(self):
        """เปิดคำขอเปิดบิลจากใบโอน (เรียกจากปุ่มบนฟอร์ม Inventory)."""
        self.ensure_one()
        direction = self._od19_billing_direction()
        if not direction:
            raise UserError(
                _(
                    "สร้างคำขอเปิดบิลได้เฉพาะใบส่งของ (outgoing) หรือใบรับของ "
                    "(incoming) เท่านั้น"
                )
            )
        if self.state != "done":
            raise UserError(_("ต้องยืนยันการโอนให้เสร็จก่อนจึงจะเปิดคำขอเปิดบิลได้"))
        request = self.env["od19.billing.request"].create(
            {
                "direction": direction,
                "origin_ref": "%s,%s" % (self._name, self.id),
                "partner_id": self.partner_id.id,
            }
        )
        moves = self._od19_billing_pullable_moves()
        if moves:
            request._od19_pull_apply(self, moves)
        return {
            "type": "ir.actions.act_window",
            "name": _("Billing Request / คำขอเปิดบิล"),
            "res_model": "od19.billing.request",
            "res_id": request.id,
            "view_mode": "form",
            "target": "current",
        }
