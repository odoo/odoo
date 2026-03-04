from odoo import fields, models


class SignLog(models.Model):
    _name = "sign.log"
    _description = "Sign Request Log"
    _order = "log_date desc, id desc"

    sign_request_id = fields.Many2one(
        comodel_name="sign.request",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sign_request_item_id = fields.Many2one(
        comodel_name="sign.request.item",
        string="Request Item",
        ondelete="set null",
        index=True,
    )
    event = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("signed", "Signed"),
            ("refused", "Refused"),
            ("canceled", "Canceled"),
            ("expired", "Expired"),
            ("reminder", "Reminder"),
        ],
        required=True,
    )
    note = fields.Text()
    log_date = fields.Datetime(default=fields.Datetime.now, required=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
        ondelete="set null",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="sign_request_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )

