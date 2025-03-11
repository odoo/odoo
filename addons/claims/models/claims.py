from odoo import models, fields


class Claims(models.Model):
    _name = "claims"
    _description = "Employee claims"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Text(string="Description", required=True)
    date = fields.Date(string="Date", required=True, default=fields.Date.today())
    amount = fields.Float(string="Amount")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="draft",
        required=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
        default=lambda self: self.env.user.employee_id.id,
    )
    attachment_ids = fields.Many2many("ir.attachment", string="Attach receipts")
