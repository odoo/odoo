# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_enforce_prepare_approval = fields.Boolean(
        string="บังคับ Prepare→Approve ก่อนจ่าย (AP)",
        default=False,
        help="When enabled, an outbound (vendor) payment cannot be posted until "
        "it has passed the Prepare -> Approve steps. Disabled by default so the "
        "gate can be rolled out progressively.",
    )
    od19_enforce_prepare_sod = fields.Boolean(
        string="แยกหน้าที่ผู้จัดทำ/ผู้อนุมัติ (SoD)",
        default=True,
        help="When enabled, the user who prepared a payment cannot also approve "
        "it (segregation of duties).",
    )
