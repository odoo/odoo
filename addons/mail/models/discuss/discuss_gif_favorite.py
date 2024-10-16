# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class DiscussGifFavorite(models.Model):
    _description = "Save favorite GIF from Tenor API"

    tenor_gif_id = fields.Char("GIF id from Tenor", required=True)

    _sql_constraints = [
        (
            "user_gif_favorite",
            "unique(create_uid,tenor_gif_id)",
            "User should not have duplicated favorite GIF",
        ),
    ]

    @api.depends('create_uid', 'tenor_gif_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.create_uid.name} - {rec.tenor_gif_id}"
