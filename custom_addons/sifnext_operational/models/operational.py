from odoo import api, fields, models


class SifnextOperational(models.Model):
    _name = "sifnext.operational"
    _description = "SIFNEXT Operational"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="Nomor Operasional",
        required=True,
        readonly=True,
        copy=False,
        default="New",
        tracking=True,
    )
    description = fields.Text(string="Deskripsi")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("progress", "In Progress"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("sifnext.operational")
                    or "New"
                )
        return super().create(vals_list)

    def action_start(self):
        self.write({"state": "progress"})

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_reset_draft(self):
        self.write({"state": "draft"})
