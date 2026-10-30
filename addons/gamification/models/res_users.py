# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL


class ResUsers(models.Model):
    _inherit = 'res.users'

    karma = fields.Integer('Karma', compute='_compute_karma', store=True, readonly=False)
    karma_tracking_ids = fields.One2many('gamification.karma.tracking', 'user_id', string='Karma Changes', groups="base.group_system")
    badge_ids = fields.One2many('gamification.badge.user', 'user_id', string='Badges', copy=False)
    gold_badge = fields.Integer('Gold badges count', compute="_get_user_badge_level")
    silver_badge = fields.Integer('Silver badges count', compute="_get_user_badge_level")
    bronze_badge = fields.Integer('Bronze badges count', compute="_get_user_badge_level")
    rank_id = fields.Many2one('gamification.karma.rank', 'Rank', index='btree_not_null')
    next_rank_id = fields.Many2one('gamification.karma.rank', 'Next Rank')

    @api.depends('karma_tracking_ids.new_value')
    def _compute_karma(self):
        if self.env.context.get('skip_karma_computation'):
            # do not need to update the user karma
            # e.g. during the tracking consolidation
            return

        self.env['gamification.karma.tracking'].flush_model()

        select_query = """
            SELECT DISTINCT ON (user_id) user_id, new_value
              FROM gamification_karma_tracking
             WHERE user_id = ANY(%(user_ids)s)
          ORDER BY user_id, tracking_date DESC, id DESC
        """
        self.env.cr.execute(select_query, {'user_ids': self.ids})

        user_karma_map = {
            values['user_id']: values['new_value']
            for values in self.env.cr.dictfetchall()
        }

        for user in self:
            user.karma = user_karma_map.get(user.id, 0)

        self.sudo()._recompute_rank()

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
    def create(self, vals_list):
        res = super().create(vals_list)

        self._add_karma_batch({
            user: {
                'gain': int(vals['karma']),
                'old_value': 0,
                'origin_ref': f'res.users,{self.env.uid}',
                'reason': _('User Creation'),
            }
            for user, vals in zip(res, vals_list)
            if vals.get('karma')
        })

        return res

    def write(self, vals):
        if 'karma' in vals:
            self._add_karma_batch({
                user: {
                    'gain': int(vals['karma']) - user.karma,
                    'origin_ref': f'res.users,{self.env.uid}',
                }
                for user in self
                if int(vals['karma']) != user.karma
            })
        return super().write(vals)

    def _add_karma(self, gain, source=None, reason=None):
        self.ensure_one()
        values = {'gain': gain, 'source': source, 'reason': reason}
        return self._add_karma_batch({self: values})

    def _add_karma_batch(self, values_per_user):
        if not values_per_user:
            return

        create_values = []
        for user, values in values_per_user.items():
            origin = values.get('source') or self.env.user
            reason = values.get('reason') or _('Add Manually')
            origin_description = f'{origin.display_name} #{origin.id}'
            old_value = values.get('old_value', user.karma)

            create_values.append({
                'new_value': old_value + values['gain'],
                'old_value': old_value,
                'origin_ref': f'{origin._name},{origin.id}',
                'reason': f'{reason} ({origin_description})',
                'user_id': user.id,
            })

        self.env['gamification.karma.tracking'].sudo().create(create_values)
        return True

    @api.model
    def _get_users_karma_ranking(self, user_domain, search_domain=None, from_date=None, to_date=None,
                                 limit=30, offset=0, extra_user_ids=None):
        """ Rank the users matching ``user_domain`` by karma and return one page
        of those also matching ``search_domain``.

        Positions are computed over the whole ``user_domain`` population, so a
        user found through a search keeps their actual position in the ranking
        instead of their position within the search results. Users without any
        karma change in the timeframe are ranked too, with a gain of 0.

        :param user_domain: users taking part in the ranking (i.e. active,
          karma > 1, website published, ...)
        :param search_domain: optional domain restricting the returned users;
          it does not impact positions, only which users are paginated
        :param from_date: rank on karma gained since this date (included)
        :param to_date: rank on karma gained until this date (included);
          without any date, rank on total karma
        :param limit: page size, counted on users matching both domains
        :param offset: page offset, counted on users matching both domains
        :param extra_user_ids: ids of users to return even when outside of the
          page, provided they match both domains; e.g. the current user, to
          show their own position below the page

        :rtype: dict
        :return: ``{user_id: row}`` ordered by position, each row being:
          ::

            {
                'user_id': int,
                'karma_gain': int, karma gained in the timeframe (total karma without dates),
                'karma_position': int, position in the ranking of ``user_domain``,
                'in_page': bool, whether the user belongs to the requested page
                  (False only for ``extra_user_ids`` outside of it),
            }
        """
        query = self._search(user_domain, bypass_access=True)
        user_t = query.table
        if from_date or to_date:
            tracking_domain = Domain.TRUE
            if from_date:
                tracking_domain &= Domain('tracking_date', '>=', from_date)
            if to_date:
                tracking_domain &= Domain('tracking_date', '<=', to_date)
            # aggregate the gains per user before joining, to group only the trackings of the timeframe
            tracking_query = self.env['gamification.karma.tracking']._search(tracking_domain, bypass_access=True)
            tracking_t = tracking_query.table
            tracking_query.groupby = tracking_t.user_id
            tracking_subquery = tracking_query.subselect(
                SQL("%s AS user_id", tracking_t.user_id),
                SQL("SUM(%s - %s) AS karma_gain", tracking_t.new_value, tracking_t.old_value),
            )
            gain_t = user_t._make_alias('karma_gain')
            # left join: users without tracking in the timeframe are ranked with a gain of 0
            query.add_join('LEFT JOIN', gain_t, tracking_subquery, SQL("%s = %s", gain_t.user_id, user_t.id))
            karma_gain = SQL("COALESCE(%s, 0)", gain_t.karma_gain)
        else:
            karma_gain = SQL("COALESCE(%s, 0)", user_t.karma)
        karma_query = query.subselect(SQL("%s AS user_id", user_t.id), SQL("%s AS karma_gain", karma_gain))

        if limit is None:
            page_condition = SQL("row_index > %s", offset)
        else:
            page_condition = SQL("row_index > %s AND row_index <= %s", offset, offset + limit)

        if search_domain:
            row_index = SQL("ROW_NUMBER() OVER (ORDER BY karma_position)")
            search_condition = SQL("user_id IN %s", self._search(search_domain, bypass_access=True).subselect())
        else:
            # without search, the page rows are the ranking ones: skip the second sort
            row_index = SQL("karma_position")
            search_condition = SQL("TRUE")

        rows = self.env.execute_query_dict(SQL("""
            WITH ranked_users AS (
                SELECT user_id,
                       karma_gain,
                       ROW_NUMBER() OVER (ORDER BY karma_gain DESC, user_id DESC) AS karma_position
                  FROM %(karma_query)s
            ),
            searched_users AS (
                SELECT user_id,
                       karma_gain,
                       karma_position,
                       %(row_index)s AS row_index
                  FROM ranked_users
                 WHERE %(search_condition)s
            )
            SELECT user_id,
                   karma_gain,
                   karma_position,
                   %(page_condition)s AS in_page
              FROM searched_users
             WHERE %(page_condition)s %(or_extra_user)s
          ORDER BY karma_position
        """,
            karma_query=karma_query,
            row_index=row_index,
            search_condition=search_condition,
            page_condition=page_condition,
            or_extra_user=SQL("OR user_id IN %s", tuple(extra_user_ids)) if extra_user_ids else SQL(),
        ))
        return {row['user_id']: row for row in rows}

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
        else:
            domain = [('karma_min', '>', self.rank_id.karma_min)] if self.rank_id else []
            return self.env['gamification.karma.rank'].search(domain, order="karma_min ASC", limit=1)

    def get_gamification_redirection_data(self):
        """
        Hook for other modules to add redirect button(s) in new rank reached mail
        Must return a list of dictionnary including url and label.
        E.g. return [{'url': '/forum', label: 'Go to Forum'}]
        """
        self.ensure_one()
        return []

    def action_karma_report(self):
        self.ensure_one()

        return {
            'name': _('Karma Updates'),
            'res_model': 'gamification.karma.tracking',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'context': {
                'default_user_id': self.id,
                'search_default_user_id': self.id,
            },
        }
