from odoo import fields, models


class MixinFavorite(models.AbstractModel):
    _name = "mixin.favorite"
    _description = "Favorite Mixin"

    is_favorite = fields.Boolean(string="Favorite")
