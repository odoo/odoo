from odoo import api, fields, models


class AIUseCaseTag(models.Model):
    _name = "ai.use.case.tag"
    _inherit = ["mixin.catalog"]
    _description = "AI Use Case Tag"
    _order = "sequence, name"

    name = fields.Char(
        string="Tag Name",
        help="Human-readable tag name (e.g., 'Vision Processing')",
    )
    code = fields.Char(
        index=True,
        required=True,
        help="Unique identifier used in code (e.g., 'vision', 'reasoning')",
    )
    sequence = fields.Integer(default=10)
    description = fields.Text(
        translate=True,
        help="What this use case represents and when to use it",
    )
    color = fields.Integer(help="Color for UI display")
    _code_uniq = models.Constraint(
        "unique(code)",
        "Use case tag code must be unique!",
    )

    @api.depends("name", "code")
    def _compute_display_name(self) -> None:
        for record in self:
            record.display_name = f"{record.name} [{record.code}]"
