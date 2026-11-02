from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    od19_ar_billing_mode = fields.Selection(
        [
            ("default", "Use Company Default / ตามบริษัท"),
            ("direct", "Direct / ออกบิลเลย"),
            ("two_step", "Two Step / วางบิลก่อน"),
        ],
        string="AR Billing Mode",
        default="default",
    )
