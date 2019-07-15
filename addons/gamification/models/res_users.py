# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)

class Users(models.Model):
    _inherit = 'res.users'

    karma = fields.Integer('Karma', default=0)
    karma_position = fields.Integer('Karma position', compute="_compute_karma_position", store=False)
    badge_ids = fields.One2many('gamification.badge.user', 'user_id', string='Badges', copy=False)
    gold_badge = fields.Integer('Gold badges count', compute="_get_user_badge_level")
    silver_badge = fields.Integer('Silver badges count', compute="_get_user_badge_level")
    bronze_badge = fields.Integer('Bronze badges count', compute="_get_user_badge_level")
    rank_id = fields.Many2one('gamification.karma.rank', 'Rank', index=False)
    next_rank_id = fields.Many2one('gamification.karma.rank', 'Next Rank', index=False)

    @api.depends('karma')
    def _compute_karma_position(self):
        _logger.warning("The field karma_position from res.users is deprecated. Don't use it anymore.")
        for user in self:
            user.karma_position = 0

    @api.multi
    @api.depends('badge_ids')
    def _get_user_badge_level(self):
        """ Return total badge per level of users
        TDE CLEANME: shouldn't check type is forum ? """
        for user in self:
            user.gold_badge = 0
            user.silver_badge = 0
            user.bronze_badge = 0

        self.env.cr.execute("""
            SELECT bu.user_id, b.level, count(1)
            FROM gamification_badge_user bu, gamification_badge b
            WHERE bu.user_id IN %s
              AND bu.badge_id = b.id
              AND b.level IS NOT NULL
            GROUP BY bu.user_id, b.level
            ORDER BY bu.user_id;
        """, [tuple(self.ids)])

        for (user_id, level, count) in self.env.cr.fetchall():
            # levels are gold, silver, bronze but fields have _badge postfix
            self.browse(user_id)['{}_badge'.format(level)] = count

    @api.model_create_multi
    def create(self, values_list):
        res = super(Users, self).create(values_list)
        res._recompute_rank()
        return res

    @api.multi
    def write(self, vals):
        result = super(Users, self).write(vals)
        if 'karma' in vals:
            self._recompute_rank()
        return result

    @api.multi
    def add_karma(self, karma):
        for user in self:
            user.karma += karma
        return True

    def _rank_changed(self):
        if self.rank_id.karma_min > 0:
            template = self.env.ref('gamification.mail_template_data_new_rank_reached', raise_if_not_found=False)
            if template:
                template.send_mail(self.id, force_send=True, notif_layout='mail.mail_notification_light')

    def _recompute_rank(self):
        """
        The caller should filter the users on karma > 0 before calling this method
        to avoid looping on every single users
        """
        ranks = [{'rank': rank, 'karma_min': rank.karma_min} for rank in
                 self.env['gamification.karma.rank'].search([], order="karma_min DESC")]
        for user in self:
            old_rank = user.rank_id
            if user.karma == 0 and ranks:
                user.write({'next_rank_id': ranks[-1]['rank'].id})
            else:
                for i in range(0, len(ranks)):
                    if user.karma >= ranks[i]['karma_min']:
                        user.write({
                            'rank_id': ranks[i]['rank'].id,
                            'next_rank_id': ranks[i - 1]['rank'].id if 0 < i else False
                        })
                        break
            if old_rank != user.rank_id:
                user._rank_changed()

    def _get_next_rank(self):
        """ For fresh users with 0 karma that don't have a rank_id and next_rank_id yet
        this method returns the first karma rank (by karma ascending). This acts as a
        default value in related views.

        TDE FIXME in post-12.4: make next_rank_id a non-stored computed field correctly computed """
        return self.next_rank_id or (not self.rank_id and self.env['gamification.karma.rank'].search([], order="karma_min ASC", limit=1))

    def get_gamification_redirection_data(self):
        """
        Hook for other modules to add redirect button(s) in new rank reached mail
        Must return a list of dictionnary including url and label.
        E.g. return [{'url': '/forum', label: 'Go to Forum'}]
        """
        self.ensure_one()
        return []
