from odoo import fields, models


class ForgeField(models.Model):
    _name = "forge.field"
    _description = "Forge Field"

    name = fields.Char(required=True, help="Python field name")
    string = fields.Char(required=True, help="UI label")
    field_type = fields.Selection(
        [
            ("char", "Char"),
            ("text", "Text"),
            ("integer", "Integer"),
            ("float", "Float"),
            ("boolean", "Boolean"),
            ("date", "Date"),
            ("datetime", "Datetime"),
            ("many2one", "Many2one"),
            ("one2many", "One2many"),
            ("many2many", "Many2many"),
        ],
        required=True,
    )
    model_id = fields.Many2one("forge.model", required=True, ondelete="cascade")
    relation_model = fields.Char(
        help="For relational fields: target model technical name"
    )
    relation_field = fields.Char(help="For one2many: inverse field name")
    required = fields.Boolean(default=False)
    index = fields.Boolean(default=False)
    default_value = fields.Char()
