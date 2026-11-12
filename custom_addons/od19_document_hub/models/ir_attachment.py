# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


ORIGIN_SELECTION = [
    ("external", "รับจากภายนอก"),
    ("internal", "สร้างจากระบบ"),
    ("legacy15", "ยกมาจาก Odoo 15"),
]

CONFIDENTIALITY_SELECTION = [
    ("public", "สาธารณะ"),
    ("internal", "ภายใน"),
    ("confidential", "ความลับ"),
    ("secret", "ลับมาก"),
]

INDEX_STATE_SELECTION = [
    ("none", "ยังไม่เข้าคิว"),
    ("pending", "รอสกัด"),
    ("done", "สกัดแล้ว"),
    ("failed", "ล้มเหลว"),
    ("skipped", "ข้าม"),
]


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    od19_category_id = fields.Many2one(
        "od19.document.category", "หมวดเอกสาร", ondelete="restrict", index=True,
    )
    od19_origin = fields.Selection(
        ORIGIN_SELECTION, "ที่มา", default="external", index=True,
    )
    od19_doc_date = fields.Date("วันที่บนเอกสาร", index=True)
    od19_partner_id = fields.Many2one(
        "res.partner", "คู่ค้า", ondelete="set null", index=True,
    )
    od19_department_id = fields.Many2one(
        "hr.department", "แผนก", ondelete="set null", index=True,
    )
    od19_confidentiality = fields.Selection(
        CONFIDENTIALITY_SELECTION, "ระดับความลับ", default="internal", index=True,
    )
    od19_retention_policy_id = fields.Many2one(
        "od19.document.retention.policy", "นโยบายอายุ", ondelete="restrict",
    )
    od19_retention_until = fields.Date(
        "ครบกำหนดเก็บรักษา",
        compute="_compute_od19_retention_until",
        store=True,
        readonly=True,
        index=True,
    )
    od19_legal_hold = fields.Boolean("ห้ามทำลาย", index=True)
    od19_index_state = fields.Selection(
        INDEX_STATE_SELECTION, "สถานะสกัดข้อความ", default="none", index=True,
    )
    od19_indexed_at = fields.Datetime("สกัดเมื่อ", readonly=True)
    od19_source_ref = fields.Char(
        "เลขอ้างอิงต้นทาง", help="เลขที่เอกสารต้นทางที่ระบบสร้าง",
    )
    od19_duplicate_count = fields.Integer(
        "ระเบียนที่ใช้ไฟล์เดียวกัน", compute="_compute_od19_duplicate_count",
    )

    _od19_name_trgm = models.Index("USING gin (name gin_trgm_ops)")
    _od19_checksum_idx = models.Index("(checksum)")

    @api.depends(
        "od19_doc_date",
        "od19_retention_policy_id",
        "od19_retention_policy_id.duration_month",
    )
    def _compute_od19_retention_until(self):
        for attachment in self:
            policy = attachment.od19_retention_policy_id
            base_date = attachment.od19_doc_date
            if policy and policy.duration_month and base_date:
                attachment.od19_retention_until = fields.Date.add(
                    base_date, months=policy.duration_month,
                )
            else:
                attachment.od19_retention_until = False

    @api.depends("checksum")
    def _compute_od19_duplicate_count(self):
        for attachment in self:
            if attachment.checksum:
                attachment.od19_duplicate_count = self.search_count([
                    ("checksum", "=", attachment.checksum),
                    ("id", "!=", attachment.id),
                ])
            else:
                attachment.od19_duplicate_count = 0
