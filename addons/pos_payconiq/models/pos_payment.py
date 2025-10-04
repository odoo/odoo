from odoo import fields, models


class PosPayment(models.Model):
    _inherit = "pos.payment"

    payconiq_id = fields.Char(
        "Payconiq ID",
        readonly=True,
        copy=False,
    )
