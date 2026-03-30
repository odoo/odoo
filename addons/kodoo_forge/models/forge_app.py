from odoo import fields, models


class ForgeApp(models.Model):
    _name = "forge.app"
    _description = "Forge App"
    _technical_name_uniq = models.Constraint(
        "UNIQUE (technical_name)",
        "Technical name must be unique",
    )

    name = fields.Char(string="Name", required=True)
    technical_name = fields.Char(string="Technical Name", required=True)
    description = fields.Text()
