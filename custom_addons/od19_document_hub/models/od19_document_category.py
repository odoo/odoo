# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class Od19DocumentCategory(models.Model):
    _name = "od19.document.category"
    _description = "หมวดหมู่เอกสาร"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = "complete_name"
    _order = "complete_name, id"

    name = fields.Char("ชื่อหมวด", required=True, translate=True)
    code = fields.Char("รหัส", required=True)
    complete_name = fields.Char(
        "ชื่อเต็ม", compute="_compute_complete_name", store=True, recursive=True,
    )
    parent_id = fields.Many2one(
        "od19.document.category", "หมวดแม่", ondelete="restrict", index=True,
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        "od19.document.category", "parent_id", "หมวดย่อย",
    )
    default_retention_policy_id = fields.Many2one(
        "od19.document.retention.policy", "นโยบายอายุเริ่มต้น", ondelete="restrict",
    )
    auto_classify = fields.Boolean("จัดหมวดอัตโนมัติ", default=True)
    allowed_models = fields.Char(
        "โมเดลที่ผูกได้",
        help="รายชื่อ res_model คั่นด้วยจุลภาค ถ้าว่าง = ผูกได้ทุกโมเดล",
    )
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint("UNIQUE(code)", "รหัสหมวดต้องไม่ซ้ำ")

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = (
                    f"{category.parent_id.complete_name} / {category.name}"
                )
            else:
                category.complete_name = category.name
