from odoo import fields, models


class PosPaymentPayconiq(models.Model):
    _name = "pos.payment.payconiq"
    _description = "Payconiq Payment Metadata"
    _order = "create_date desc"

    uuid = fields.Char(
        "POS Payment UUID",
        readonly=True,
        copy=False,
    )
    payconiq_id = fields.Char(
        "Payconiq ID",
        readonly=True,
        copy=False,
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        readonly=True,
        default=lambda self: self.env.user,
    )
    qr_code = fields.Char(
        "QR Code",
        readonly=True,
        copy=False,
    )
    state = fields.Selection(
        selection=[
            ("created", "Created"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        readonly=True,
        default="created",
    )
