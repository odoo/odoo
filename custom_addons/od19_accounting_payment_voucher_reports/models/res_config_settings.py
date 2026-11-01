# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_enforce_prepare_approval = fields.Boolean(
        related="company_id.od19_enforce_prepare_approval",
        readonly=False,
        string="บังคับ Prepare→Approve ก่อนจ่าย (AP)",
        help="Require an outbound (vendor) payment to be prepared and approved "
        "before it can be posted.",
    )
    od19_enforce_prepare_sod = fields.Boolean(
        related="company_id.od19_enforce_prepare_sod",
        readonly=False,
        string="แยกหน้าที่ผู้จัดทำ/ผู้อนุมัติ (SoD)",
        help="Require the approver of a payment to be a different user than the "
        "one who prepared it.",
    )
