# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


RETENTION_ACTION = [
    ("review", "ทบทวนก่อนตัดสินใจ"),
    ("archive", "เก็บถาวร (Archive)"),
    ("delete", "ทำลาย (Delete)"),
]


class Od19DocumentRetentionPolicy(models.Model):
    _name = "od19.document.retention.policy"
    _description = "นโยบายการเก็บรักษาเอกสาร"
    _order = "duration_month, name"

    name = fields.Char("ชื่อนโยบาย", required=True, translate=True)
    duration_month = fields.Integer("อายุ (เดือน)", required=True, default=60)
    action = fields.Selection(
        RETENTION_ACTION, "การจัดการเมื่อครบกำหนด", required=True, default="review",
    )
    basis = fields.Char(
        "อ้างอิงกฎหมาย/เหตุผล",
        help="เช่น พระราชบัญญัติการบัญชี พ.ศ. 2543 มาตรา 14",
    )
    category_ids = fields.One2many(
        "od19.document.category", "default_retention_policy_id", "หมวดที่ใช้",
    )
    active = fields.Boolean(default=True)

    _duration_positive = models.Constraint(
        "CHECK(duration_month > 0)",
        "อายุการเก็บรักษาต้องมากกว่า 0 เดือน",
    )
