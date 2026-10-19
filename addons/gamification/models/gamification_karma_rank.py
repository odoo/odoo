# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.tools.translate import html_translate


class GamificationKarmaRank(models.Model):
    _name = 'gamification.karma.rank'
    _description = 'Rank based on karma'
    _inherit = ['image.mixin']
    _order = 'karma_min'

    name = fields.Text(string='Rank Name', translate=True, required=True)
    description = fields.Html(string='Description', translate=html_translate, sanitize_attributes=False,)
    description_motivational = fields.Html(
        string='Motivational', translate=html_translate, sanitize_attributes=False, sanitize_overridable=True,
        help="Motivational phrase to reach this rank on your profile page")
    karma_min = fields.Integer(
        string='Required Karma', required=True, default=1)
    user_ids = fields.One2many('res.users', 'rank_id', string='Users')
    rank_users_count = fields.Integer("# Users", compute="_compute_rank_users_count")

    _karma_min_check = models.Constraint(
        'CHECK( karma_min > 0 )',
        'The required karma has to be above 0.',
    )

    @api.depends('user_ids')
    def _compute_rank_users_count(self):
        requests_data = self.env['res.users']._read_group([('rank_id', '!=', False)], ['rank_id'], ['__count'])
        requests_mapped_data = {rank.id: count for rank, count in requests_data}
        for rank in self:
            rank.rank_users_count = requests_mapped_data.get(rank.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if any(res.mapped('karma_min')) > 0:
            users = self.env['res.users'].sudo().search([('karma', '>=', max(min(res.mapped('karma_min')), 1))])
            if users:
                users._recompute_rank()
        return res

    def write(self, vals):
        if 'karma_min' in vals:
            previous_ranks = self.env['gamification.karma.rank'].search([], order="karma_min DESC").ids
            low = min(vals['karma_min'], min(self.mapped('karma_min')))
            high = max(vals['karma_min'], max(self.mapped('karma_min')))

        res = super().write(vals)

        if 'karma_min' in vals:
            after_ranks = self.env['gamification.karma.rank'].search([], order="karma_min DESC").ids
            if previous_ranks != after_ranks:
                users = self.env['res.users'].sudo().search([('karma', '>=', max(low, 1))])
            else:
                users = self.env['res.users'].sudo().search([('karma', '>=', max(low, 1)), ('karma', '<=', high)])
            users._recompute_rank()
        return res

    def _can_return_content(self, field_name=None, access_token=None):
        """Make public the rank images so they can be used in `t-field="rank_id.image_1920"`
        without the need to grant the public/portal ACL to the `gamification.karma.rank` model.

        `t-field="rank_id.image_1920` is converted to, for instance,
        `<img src="/web/image/gamification.karma.rank/5/image_128/"`
        The goal of this override is to allow the `/web/image` route to return the images related this model.
        """
        if isinstance(self.env['image.mixin']._fields.get(field_name), fields.Image):
            # Allow to return the field for this model if it's an image coming from the `image.mixin` mixin
            return True
        return super()._can_return_content(field_name, access_token)
