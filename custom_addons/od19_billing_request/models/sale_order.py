from odoo import fields, models


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
