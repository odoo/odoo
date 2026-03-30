from odoo import fields, models


class ForgeAutomation(models.Model):
    _name = "forge.automation"
    _description = "Forge Automation"

    name = fields.Char(required=True)
    model_id = fields.Many2one("forge.model", required=True, ondelete="cascade")
    module_id = fields.Many2one("forge.module", required=True, ondelete="cascade")
    trigger = fields.Selection(
        [
            ("on_create", "On Create"),
            ("on_write", "On Write"),
            ("on_create_or_write", "On Create Or Write"),
            ("on_unlink", "On Unlink"),
            ("on_time", "On Time"),
        ],
        required=True,
    )
    filter_domain = fields.Char(default="[]")
    code = fields.Text()
