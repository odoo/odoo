from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_ar_billing_mode_default = fields.Selection(
        [("direct", "Direct / ออกบิลเลย"), ("two_step", "Two Step / วางบิลก่อน")],
        string="Default AR Billing Mode",
        default="direct",
    )
    od19_ar_require_evidence = fields.Boolean(
        string="Require AR Evidence before Submit", default=True
    )
    od19_ap_require_original = fields.Boolean(
        string="Require Original Vendor Document before Bill", default=True
    )
