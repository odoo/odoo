# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Users(models.Model):
    _inherit = 'res.users'

    karma = fields.Integer('Karma', default=0, copy=False)
    karma_tracking_ids = fields.One2many('gamification.karma.tracking', 'user_id', string='Karma Changes', groups="base.group_system")
    badge_ids = fields.One2many('gamification.badge.user', 'user_id', string='Badges', copy=False)
    gold_badge = fields.Integer('Gold badges count', compute="_get_user_badge_level")
    silver_badge = fields.Integer('Silver badges count', compute="_get_user_badge_level")
    bronze_badge = fields.Integer('Bronze badges count', compute="_get_user_badge_level")
    rank_id = fields.Many2one('gamification.karma.rank', 'Rank')
    next_rank_id = fields.Many2one('gamification.karma.rank', 'Next Rank')

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

        karma_trackings = []
        for user in res:
            if user.karma:
                karma_trackings.append({'user_id': user.id, 'old_value': 0, 'new_value': user.karma})
        if karma_trackings:
            self.env['gamification.karma.tracking'].sudo().create(karma_trackings)

        res._recompute_rank()
        return res

    def write(self, vals):
        karma_trackings = []
        if 'karma' in vals:
            for user in self:
                if user.karma != vals['karma']:
                    karma_trackings.append({'user_id': user.id, 'old_value': user.karma, 'new_value': vals['karma']})

        result = super(Users, self).write(vals)

        if karma_trackings:
            self.env['gamification.karma.tracking'].sudo().create(karma_trackings)
        if 'karma' in vals:
            self._recompute_rank()
        return result

    def add_karma(self, karma):
        for user in self:
            user.karma += karma
        return True

    def _get_tracking_karma_gain_position(self, user_domain, from_date=None, to_date=None):
        """ Get absolute position in term of gained karma for users. First a ranking
        of all users is done given a user_domain; then the position of each user
        belonging to the current record set is extracted.

        Example: in website profile, search users with name containing Norbert. Their
        positions should not be 1 to 4 (assuming 4 results), but their actual position
        in the karma gain ranking (with example user_domain being karma > 1,
        website published True).

        :param user_domain: general domain (i.e. active, karma > 1, website, ...)
          to compute the absolute position of the current record set
        :param from_date: compute karma gained after this date (included) or from
          beginning of time;
        :param to_date: compute karma gained before this date (included) or until
          end of time;

        :return list: [{
            'user_id': user_id (belonging to current record set),
            'karma_gain_total': integer, karma gained in the given timeframe,
            'karma_position': integer, ranking position
        }, {..}] ordered by karma_position desc
        """
        if not self:
            return []

        where_query = self.env['res.users']._where_calc(user_domain)
        user_from_clause, user_where_clause, where_clause_params = where_query.get_sql()

        params = []
        if from_date:
            date_from_condition = 'AND tracking.tracking_date::timestamp >= timestamp %s'
            params.append(from_date)
        if to_date:
            date_to_condition = 'AND tracking.tracking_date::timestamp <= timestamp %s'
            params.append(to_date)
        params.append(tuple(self.ids))

        query = """
SELECT final.user_id, final.karma_gain_total, final.karma_position
FROM (
    SELECT intermediate.user_id, intermediate.karma_gain_total, row_number() OVER (ORDER BY intermediate.karma_gain_total DESC) AS karma_position
    FROM (
        SELECT "res_users".id as user_id, COALESCE(SUM("tracking".new_value - "tracking".old_value), 0) as karma_gain_total
        FROM %(user_from_clause)s
        LEFT JOIN "gamification_karma_tracking" as "tracking"
        ON "res_users".id = "tracking".user_id AND "res_users"."active" = TRUE
        WHERE %(user_where_clause)s %(date_from_condition)s %(date_to_condition)s
        GROUP BY "res_users".id
        ORDER BY karma_gain_total DESC
    ) intermediate
) final
WHERE final.user_id IN %%s""" % {
            'user_from_clause': user_from_clause,
            'user_where_clause': user_where_clause or (not from_date and not to_date and 'TRUE') or '',
            'date_from_condition': date_from_condition if from_date else '',
            'date_to_condition': date_to_condition if to_date else ''
        }

        self.env.cr.execute(query, tuple(where_clause_params + params))
        return self.env.cr.dictfetchall()

    def _get_karma_position(self, user_domain):
        """ Get absolute position in term of total karma for users. First a ranking
        of all users is done given a user_domain; then the position of each user
        belonging to the current record set is extracted.

        Example: in website profile, search users with name containing Norbert. Their
        positions should not be 1 to 4 (assuming 4 results), but their actual position
        in the total karma ranking (with example user_domain being karma > 1,
        website published True).

        :param user_domain: general domain (i.e. active, karma > 1, website, ...)
          to compute the absolute position of the current record set

        :return list: [{
            'user_id': user_id (belonging to current record set),
            'karma_position': integer, ranking position
        }, {..}] ordered by karma_position desc
        """
        if not self:
            return {}

        where_query = self.env['res.users']._where_calc(user_domain)
        user_from_clause, user_where_clause, where_clause_params = where_query.get_sql()

        # we search on every user in the DB to get the real positioning (not the one inside the subset)
        # then, we filter to get only the subset.
        query = """
SELECT sub.user_id, sub.karma_position
FROM (
    SELECT "res_users"."id" as user_id, row_number() OVER (ORDER BY res_users.karma DESC) AS karma_position
    FROM %(user_from_clause)s
    WHERE %(user_where_clause)s
) sub
WHERE sub.user_id IN %%s""" % {
            'user_from_clause': user_from_clause,
            'user_where_clause': user_where_clause or 'TRUE',
        }

        self.env.cr.execute(query, tuple(where_clause_params + [tuple(self.ids)]))
        return self.env.cr.dictfetchall()

    def _rank_changed(self):
        """
            Method that can be called on a batch of users with the same new rank
        """
        if self.env.context.get('install_mode', False):
            # avoid sending emails in install mode (prevents spamming users when creating data ranks)
            return

        template = self.env.ref('gamification.mail_template_data_new_rank_reached', raise_if_not_found=False)
        if template:
            for u in self:
                if u.rank_id.karma_min > 0:
                    template.send_mail(u.id, force_send=False, email_layout_xmlid='mail.mail_notification_light')

    def _recompute_rank(self):
        """
        The caller should filter the users on karma > 0 before calling this method
        to avoid looping on every single users

        Compute rank of each user by user.
        For each user, check the rank of this user
        """

        ranks = [{'rank': rank, 'karma_min': rank.karma_min} for rank in
                 self.env['gamification.karma.rank'].search([], order="karma_min DESC")]

        # 3 is the number of search/requests used by rank in _recompute_rank_bulk()
        if len(self) > len(ranks) * 3:
            self._recompute_rank_bulk()
            return

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

    def _recompute_rank_bulk(self):
        """
            Compute rank of each user by rank.
            For each rank, check which users need to be ranked

        """
        ranks = [{'rank': rank, 'karma_min': rank.karma_min} for rank in
                 self.env['gamification.karma.rank'].search([], order="karma_min DESC")]

        users_todo = self

        next_rank_id = False
        # wtf, next_rank_id should be a related on rank_id.next_rank_id and life might get easier.
        # And we only need to recompute next_rank_id on write with min_karma or in the create on rank model.
        for r in ranks:
            rank_id = r['rank'].id
            dom = [
                ('karma', '>=', r['karma_min']),
                ('id', 'in', users_todo.ids),
                '|',  # noqa
                    '|', ('rank_id', '!=', rank_id), ('rank_id', '=', False),
                    '|', ('next_rank_id', '!=', next_rank_id), ('next_rank_id', '=', False if next_rank_id else -1),
            ]
            users = self.env['res.users'].search(dom)
            if users:
                users_to_notify = self.env['res.users'].search([
                    ('karma', '>=', r['karma_min']),
                    '|', ('rank_id', '!=', rank_id), ('rank_id', '=', False),
                    ('id', 'in', users.ids),
                ])
                users.write({
                    'rank_id': rank_id,
                    'next_rank_id': next_rank_id,
                })
                users_to_notify._rank_changed()
                users_todo -= users

            nothing_to_do_users = self.env['res.users'].search([
                ('karma', '>=', r['karma_min']),
                '|', ('rank_id', '=', rank_id), ('next_rank_id', '=', next_rank_id),
                ('id', 'in', users_todo.ids),
            ])
            users_todo -= nothing_to_do_users
            next_rank_id = r['rank'].id

        if ranks:
            lower_rank = ranks[-1]['rank']
            users = self.env['res.users'].search([
                ('karma', '>=', 0),
                ('karma', '<', lower_rank.karma_min),
                '|', ('rank_id', '!=', False), ('next_rank_id', '!=', lower_rank.id),
                ('id', 'in', users_todo.ids),
            ])
            if users:
                users.write({
                    'rank_id': False,
                    'next_rank_id': lower_rank.id,
                })

    def _get_next_rank(self):
        """ For fresh users with 0 karma that don't have a rank_id and next_rank_id yet
        this method returns the first karma rank (by karma ascending). This acts as a
        default value in related views.

        TDE FIXME in post-12.4: make next_rank_id a non-stored computed field correctly computed """

        if self.next_rank_id:
            return self.next_rank_id
        elif not self.rank_id:
            return self.env['gamification.karma.rank'].search([], order="karma_min ASC", limit=1)
        else:
            return self.env['gamification.karma.rank']

    def get_gamification_redirection_data(self):
        """
        Hook for other modules to add redirect button(s) in new rank reached mail
        Must return a list of dictionnary including url and label.
        E.g. return [{'url': '/forum', label: 'Go to Forum'}]
        """
        self.ensure_one()
        return []
