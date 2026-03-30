from odoo import fields, models


class ForgeBuild(models.Model):
    _name = "forge.build"
    _description = "Forge Build"

    module_id = fields.Many2one("forge.module", required=True, ondelete="cascade")
    build_date = fields.Datetime(default=fields.Datetime.now)
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("running", "Running"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    log = fields.Text()
    triggered_by = fields.Char(help='user login ou "cli" ou "api"')
