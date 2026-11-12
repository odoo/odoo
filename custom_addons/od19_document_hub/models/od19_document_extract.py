# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


ENGINE_SELECTION = [
    ("core", "Odoo Core (attachment_indexation)"),
    ("pdfminer", "pdfminer.six"),
    ("manual", "กรอกด้วยมือ"),
]


class Od19DocumentExtract(models.Model):
    _name = "od19.document.extract"
    _description = "ข้อความที่สกัดได้จากเอกสารแนบ"
    _order = "id desc"

    attachment_id = fields.Many2one(
        "ir.attachment", "เอกสารแนบ", required=True, ondelete="cascade", index=True,
    )
    text_content = fields.Text("ข้อความ", prefetch=False)
    engine = fields.Selection(ENGINE_SELECTION, "ตัวสกัด", default="pdfminer")
    quality = fields.Float("คุณภาพ", digits=(3, 2))
    lang = fields.Char("ภาษา")

    _attachment_uniq = models.Constraint(
        "unique(attachment_id)",
        "เอกสารแนบนี้มีข้อความสกัดอยู่แล้ว",
    )
    _content_trgm = models.Index("USING gin (text_content gin_trgm_ops)")
