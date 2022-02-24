# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command


class FavoriteMixin(models.AbstractModel):
    _name = 'favorite.mixin'
    _description = "Favorite Mixin"

    def _default_favorite_user_ids(self):
        return [Command.set([self.env.uid])]

    favorite_user_ids = fields.Many2many(
        'res.users',
        string="Favorite Members",
        default=_default_favorite_user_ids,
        copy=False)
    is_favorite = fields.Boolean(
        string="Show on dashboard",
        compute='_compute_is_favorite', inverse='_inverse_is_favorite',
        help="Favorite teams to display them in the dashboard and access them easily.")

    @api.depends_context('uid')
    @api.depends('favorite_user_ids')
    def _compute_is_favorite(self):
        for team in self:
            team.is_favorite = self.env.user in team.favorite_user_ids

    def _inverse_is_favorite(self):
        sudoed_self = self.sudo()
        to_fav = sudoed_self.filtered(lambda team: self.env.user not in team.favorite_user_ids)
        to_fav.write({'favorite_user_ids': [Command.link(self.env.uid)]})
        (sudoed_self - to_fav).write({'favorite_user_ids': [Command.unlink(self.env.uid)]})

    def toggle_is_favorite(self):
        fav_records = self.filtered(lambda rec: rec.env.user in rec.favorite_user_ids)
        fav_records.favorite_user_ids = [Command.unlink(self.env.uid)]
        (self - fav_records).favorite_user_ids = [Command.link(self.env.uid)]
