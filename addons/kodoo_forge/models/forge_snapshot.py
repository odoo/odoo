from odoo import fields, models


class ForgeSnapshot(models.Model):
    _name = "forge.snapshot"
    _description = "Forge Snapshot"

    module_id = fields.Many2one("forge.module", required=True, ondelete="cascade")
    name = fields.Char(required=True)
    created_at = fields.Datetime(default=fields.Datetime.now)
    created_by = fields.Char()
    state_json = fields.Text(
        required=True,
        help="Self-contained JSON snapshot of entire module definition",
    )
