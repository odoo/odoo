# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.tools.translate import html_translate


class KarmaRank(models.Model):
    _name = 'gamification.karma.rank'
    _description = 'Rank based on karma'
    _inherit = 'image.mixin'
    _order = 'karma_min'

    name = fields.Text(string='Rank Name', translate=True, required=True)
    description = fields.Html(string='Description', translate=html_translate, sanitize_attributes=False,)
    description_motivational = fields.Html(
        string='Motivational', translate=html_translate, sanitize_attributes=False,
        help="Motivational phrase to reach this rank")
    karma_min = fields.Integer(
        string='Required Karma', required=True, default=1,
        help='Minimum karma needed to reach this rank')
    user_ids = fields.One2many('res.users', 'rank_id', string='Users', help="Users having this rank")
    rank_users_count = fields.Integer("# Users", compute="_compute_rank_users_count")

    _sql_constraints = [
        ('karma_min_check', "CHECK( karma_min > 0 )", 'The required karma has to be above 0.')
    ]

    @api.depends('user_ids')
    def _compute_rank_users_count(self):
        requests_data = self.env['res.users'].read_group([('rank_id', '!=', False)], ['rank_id'], ['rank_id'])
        requests_mapped_data = dict((data['rank_id'][0], data['rank_id_count']) for data in requests_data)
        for rank in self:
            rank.rank_users_count = requests_mapped_data.get(rank.id, 0)

    @api.model_create_multi
    def create(self, values_list):
        res = super(KarmaRank, self).create(values_list)
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

        res = super(KarmaRank, self).write(vals)

        if 'karma_min' in vals:
            after_ranks = self.env['gamification.karma.rank'].search([], order="karma_min DESC").ids
            if previous_ranks != after_ranks:
                users = self.env['res.users'].sudo().search([('karma', '>=', max(low, 1))])
            else:
                users = self.env['res.users'].sudo().search([('karma', '>=', max(low, 1)), ('karma', '<=', high)])
            users._recompute_rank()
        return res
