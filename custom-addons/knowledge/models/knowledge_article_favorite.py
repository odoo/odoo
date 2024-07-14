# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _


class ArticleFavorite(models.Model):
    _name = 'knowledge.article.favorite'
    _description = 'Favorite Article'
    _order = 'sequence ASC, id DESC'
    _rec_name = 'article_id'

    article_id = fields.Many2one(
        'knowledge.article', 'Article',
        index=True, required=True, ondelete='cascade')
    user_id = fields.Many2one(
        'res.users', 'User',
        index=True, required=True, ondelete='cascade')
    is_article_active = fields.Boolean('Is Article Active', related='article_id.active',
        store=True, readonly=True)
    sequence = fields.Integer(default=0)

    _sql_constraints = [
        ('unique_article_user',
         'unique(article_id, user_id)',
         'User already has this article in favorites.')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """ At creation, we need to set the max sequence, if not given, for each favorite to create, in order to keep
        a correct ordering as much as possible. Some sequence could be given in create values, that could lead to
        duplicated sequence per user_id. That is not an issue as they will be resequenced the next time the user reorder
        their favorites. """
        # TDE TODO: env.uid -> user_id
        default_sequence = 1
        if any(not vals.get('sequence') for vals in vals_list):
            favorite = self.env['knowledge.article.favorite'].search(
                [('user_id', '=', self.env.uid)],
                order='sequence DESC',
                limit=1
            )
            default_sequence = favorite.sequence + 1 if favorite else default_sequence
        for vals in vals_list:
            if not vals.get('sequence'):
                vals['sequence'] = default_sequence
                default_sequence += 1
        return super(ArticleFavorite, self).create(vals_list)

    def write(self, vals):
        """ Whatever rights, avoid any attempt at privilege escalation. """
        if ('article_id' in vals or 'user_id' in vals) and not self.env.is_admin():
            raise exceptions.AccessError(_("Can not update the article or user of a favorite."))
        return super().write(vals)

    def resequence_favorites(self, article_ids):
        # Some article may not be accessible by the user anymore. Therefore,
        # to prevent an access error, one will only resequence the favorites
        # related to the articles accessible by the user
        sequence = 0
        # Keep the same order as in article_ids
        for article_id in article_ids:
            self.search([('article_id', '=', article_id), ('user_id', '=', self.env.uid)]).write({"sequence": sequence})
            sequence += 1
