from odoo import fields, models


class ForgeModule(models.Model):
    _name = "forge.module"
    _description = "Forge Module"
    _technical_name_per_app = models.Constraint(
        "UNIQUE (technical_name, app_id)",
        "Technical name must be unique per app",
    )

    name = fields.Char(required=True)
    technical_name = fields.Char(required=True)
    app_id = fields.Many2one("forge.app", required=True, ondelete="cascade")
    version = fields.Char(default="19.0.1.0.0")
    depends = fields.Char(default="base", help="Comma-separated list")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("validated", "Validated"),
            ("built", "Built"),
            ("published", "Published"),
        ],
        default="draft",
    )
