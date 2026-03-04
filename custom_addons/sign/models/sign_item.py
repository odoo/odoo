from odoo import fields, models


class SignItem(models.Model):
    _name = "sign.item"
    _description = "Sign Template Item"
    _order = "page, id"

    template_id = fields.Many2one(
        comodel_name="sign.template",
        required=True,
        ondelete="cascade",
        index=True,
    )
    type_id = fields.Many2one(
        comodel_name="sign.item.type",
        required=True,
        ondelete="restrict",
        index=True,
    )
    required = fields.Boolean(default=True)
    page = fields.Integer(default=1)
    posX = fields.Float(string="Position X", default=0.1)
    posY = fields.Float(string="Position Y", default=0.1)
    width = fields.Float(default=0.2)
    height = fields.Float(default=0.05)
    name = fields.Char(required=True)

    _page_positive = models.Constraint(
        "CHECK(page > 0)",
        "Page must be greater than zero.",
    )
    _width_positive = models.Constraint(
        "CHECK(width > 0)",
        "Width must be greater than zero.",
    )
    _height_positive = models.Constraint(
        "CHECK(height > 0)",
        "Height must be greater than zero.",
    )
