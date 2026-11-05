# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_ar_billing_mode = fields.Selection(
        [
            ("default", "Use Partner/Company Default / ตามค่าปริยาย"),
            ("direct", "Direct / ออกบิลเลย"),
            ("two_step", "Two Step / วางบิลก่อน"),
        ],
        string="AR Billing Mode",
        default="default",
    )

    def action_od19_create_billing_request(self):
        """เปิดคำขอเปิดบิล (AR) จากใบสั่งขาย (เรียกจากปุ่มบนฟอร์ม Sale Order).

        ดึงเฉพาะบรรทัดที่ยังเปิดบิลได้ (``qty_to_invoice > 0``) เท่านั้น:
        บรรทัดที่ออกบิลไปบางส่วนจะเหลือเฉพาะยอดที่ยังไม่ถูกเปิดบิล และบรรทัด
        ที่ออกบิลครบแล้วจะไม่ถูกดึงเข้ามาเลย.
        """
        self.ensure_one()
        if self.state != "sale":
            raise UserError(_("ต้องยืนยันใบสั่งขายก่อนจึงจะเปิดคำขอเปิดบิลได้"))
        request = self.env["od19.billing.request"].create(
            {
                "direction": "ar",
                "origin_ref": "%s,%s" % (self._name, self.id),
                "partner_id": self.partner_id.id,
            }
        )
        lines = request._od19_pull_candidate_lines(self)
        if lines:
            request._od19_pull_apply(self, lines)
        return {
            "type": "ir.actions.act_window",
            "name": _("Billing Request / คำขอเปิดบิล"),
            "res_model": "od19.billing.request",
            "res_id": request.id,
            "view_mode": "form",
            "target": "current",
        }
