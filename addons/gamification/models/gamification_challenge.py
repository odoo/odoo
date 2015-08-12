# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar
import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import ustr
from odoo.tools.safe_eval import safe_eval as eval

_logger = logging.getLogger(__name__)

# display top 3 in ranking, could be db variable
MAX_VISIBILITY_RANKING = 3


def start_end_date_for_period(period, default_start_date=False, default_end_date=False):
    """Return the start and end date for a goal period based on today

    :param str default_start_date: string date in DEFAULT_SERVER_DATE_FORMAT format
    :param str default_end_date: string date in DEFAULT_SERVER_DATE_FORMAT format

    :return: (start_date, end_date), dates in string format, False if the period is
    not defined or unknown"""
    today = fields.Date.from_string(fields.Date.today())
    if period == 'daily':
        start_date = today
        end_date = start_date
    elif period == 'weekly':
        delta = timedelta(days=today.weekday())
        start_date = today - delta
        end_date = start_date + timedelta(days=7)
    elif period == 'monthly':
        month_range = calendar.monthrange(today.year, today.month)
        start_date = today.replace(day=1)
        end_date = today.replace(day=month_range[1])
    elif period == 'yearly':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
    else:  # period == 'once':
        # for manual goal, start each time
        return (default_start_date, default_end_date)

    return (fields.Datetime.to_string(start_date), fields.Datetime.to_string(end_date))


class GamificationChallenge(models.Model):
    """Gamification challenge

    Set of predifined objectives assigned to people with rules for recurrence and
    rewards

    If 'user_ids' is defined and 'period' is different than 'one', the set will
    be assigned to the users for each period (eg: every 1st of each month if
    'monthly' is selected)
    """

    _name = 'gamification.challenge'
    _description = 'Gamification challenge'
    _inherit = 'mail.thread'
    _order = 'end_date, start_date, name, id'

    def _get_report_template(self):
        return self.env.ref('gamification.simple_report_template', False)

    def _get_categories(self):
        return [
            ('hr', 'Human Resources / Engagement'),
            ('other', 'Settings / Gamification Tools'),
        ]

    name = fields.Char(string='Challenge Name', required=True, translate=True)
    description = fields.Text(translate=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('inprogress', 'In Progress'),
            ('done', 'Done'),
        ], copy=False, default='draft', required=True, track_visibility='onchange')
    manager_id = fields.Many2one(
        'res.users', default=lambda self: self.env.uid,
        string='Responsible', help="The user responsible for the challenge.")

    user_ids = fields.Many2many(
        'res.users', 'gamification_challenge_users_rel',
        string='Users', help="List of users participating to the challenge")
    user_domain = fields.Char(help="Alternative to a list of users")

    period = fields.Selection(
        [
            ('once', 'Non recurring'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly')
        ], string='Periodicity', default='once',
        help='Period of automatic goal assigment. If none is selected, should be launched manually.', required=True)
    start_date = fields.Date(help="The day a new challenge will be automatically started. If no periodicity is set, will use this date as the goal start date.")
    end_date = fields.Date(help="The day a new challenge will be automatically closed. If no periodicity is set, will use this date as the goal end date.")

    invited_user_ids = fields.Many2many('res.users', 'gamification_invited_user_ids_rel', string="Suggest to users")

    line_ids = fields.One2many(
        'gamification.challenge.line', 'challenge_id',
        string='Lines', help="List of goals that will be set", required=True, copy=True)

    reward_id = fields.Many2one('gamification.badge', string="For Every Succeeding User")
    reward_first_id = fields.Many2one('gamification.badge', string="For 1st user")
    reward_second_id = fields.Many2one('gamification.badge', string="For 2nd user")
    reward_third_id = fields.Many2one('gamification.badge', string="For 3rd user")
    reward_failure = fields.Boolean('Reward Bests if not Succeeded?')
    reward_realtime = fields.Boolean(
        'Reward as soon as every goal is reached', default=True,
        help="With this option enabled, a user can receive a badge only once. The top 3 badges are still rewarded only at the end of the challenge.")

    visibility_mode = fields.Selection(
        [
            ('personal', 'Individual Goals'),
            ('ranking', 'Leader Board (Group Ranking)'),
        ], default='personal', string="Display Mode", required=True)

    report_message_frequency = fields.Selection(
        [
            ('never', 'Never'),
            ('onchange', 'On change'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly')
        ], default='never', string="Report Frequency", required=True)
    report_message_group_id = fields.Many2one(
        'mail.channel', string='Send a copy to',
        help='Group that will receive a copy of the report in addition to the user')
    report_template_id = fields.Many2one('mail.template', string="Report Template", required=True, default=_get_report_template)
    remind_update_delay = fields.Integer(
        string='Non-updated manual goals will be reminded after',
        help="Never reminded if no value or zero is specified.")
    last_report_date = fields.Date(default=fields.Date.today)
    next_report_date = fields.Date(compute="_compute_next_report_date", store=True)

    category = fields.Selection(
        '_get_categories', default='hr',
        string="Appears in", help="Define the visibility of the challenge through menus", required=True)

    @api.depends('last_report_date', 'report_message_frequency')
    def _compute_next_report_date(self):
        """Return the next report date based on the last report date and report
        period.

        :return: a string in DEFAULT_SERVER_DATE_FORMAT representing the date"""
        for challenge in self:
            last_report_date = fields.Date.from_string(challenge.last_report_date)
            if challenge.report_message_frequency == 'daily':
                challenge.next_report_date = last_report_date + timedelta(days=1)
            elif challenge.report_message_frequency == 'weekly':
                challenge.next_report_date = last_report_date + timedelta(days=7)
            elif challenge.report_message_frequency == 'monthly':
                month_range = calendar.monthrange(last_report_date.year, last_report_date.month)
                challenge.next_report_date = last_report_date.replace(day=month_range[1]) + timedelta(days=1)
            elif challenge.report_message_frequency == 'yearly':
                challenge.next_report_date = fields.Date.to_string(last_report_date.replace(year=last_report_date.year + 1))
            # frequency == 'once', reported when closed only
            else:
                challenge.next_report_date = False

    def _update_vals(self, vals):
        if vals.get('user_domain'):
            users = self._get_challenger_users(vals.get('user_domain'))
            if not vals.get('user_ids'):
                vals['user_ids'] = []
            vals['user_ids'] += [(4, user.id) for user in users]
        return vals

    @api.model
    def create(self, vals):
        """Overwrite the create method to add the user of groups"""
        return super(GamificationChallenge, self).create(self._update_vals(vals))

    @api.multi
    def write(self, vals):
        result = super(GamificationChallenge, self).write(self._update_vals(vals))

        if vals.get('report_message_frequency', 'never') != 'never':
            # _recompute_challenge_users do not set users for challenges with no reports, subscribing them now
            for challenge in self:
                challenge.message_subscribe(challenge.mapped('user_ids.partner_id').ids)

        if vals.get('state') == 'inprogress':
            self._recompute_challenge_users()
            self._generate_goals_from_challenge()

        elif vals.get('state') == 'done':
            self.check_challenge_reward(force=True)

        elif vals.get('state') == 'draft':
            # resetting progress
            if self.env['gamification.goal'].search([('challenge_id', 'in', self.ids), ('state', '=', 'inprogress')]):
                raise UserError(_("You can not reset a challenge with unfinished goals."))

        return result

    @api.multi
    def action_start(self):
        """Start a challenge"""
        return self.write({'state': 'inprogress'})

    @api.multi
    def action_check(self):
        """Check a challenge

        Create goals that haven't been created yet (eg: if added users)
        Recompute the current value for each goal related"""
        self.env['gamification.goal'].search([('challenge_id', 'in', self.ids), ('state', '=', 'inprogress')]).unlink()
        return self._update_all()

    @api.multi
    def action_report_progress(self):
        """Manual report of a goal, does not influence automatic report frequency"""
        for challenge in self:
            challenge.report_progress()
        return True

    ##### Update #####
    @api.model
    def _cron_update(self):
        """Daily cron check.

        - Start planned challenges (in draft and with start_date = today)
        - Create the missing goals (eg: modified the challenge to add lines)
        - Update every running challenge
        """
        # start scheduled challenges
        self.search([
            ('state', '=', 'draft'),
            ('start_date', '<=', fields.Date.today())
        ]).write({'state': 'inprogress'})

        # close scheduled challenges
        self.search([
            ('state', '=', 'inprogress'),
            ('end_date', '>=', fields.Date.today())
        ]).write({'state': 'done'})

        # in cron mode, will do intermediate commits
        # TODO in trunk: replace by parameter
        if not self:
            return self.search([('state', '=', 'inprogress')]).with_context(commit_gamification=True)._update_all()
        return self.with_context(commit_gamification=True)._update_all()

    def _update_all(self):
        """Update the challenges and related goals

        :param list(int) ids: the ids of the challenges to update, if False will
        update only challenges in progress."""
        if not self:
            return True

        Goal = self.env['gamification.goal']

        # include yesterday goals to update the goals that just ended
        # exclude goals for users that did not connect since the last update
        yesterday = fields.Date.from_string(fields.Date.today()) - timedelta(days=1)
        self.env.cr.execute("""SELECT gg.id
                        FROM gamification_goal as gg,
                             gamification_challenge as gc,
                             res_users as ru,
                             res_users_log as log
                       WHERE gg.challenge_id = gc.id
                         AND gg.user_id = ru.id
                         AND ru.id = log.create_uid
                         AND gg.write_date < log.create_date
                         AND gg.closed IS false
                         AND gc.id IN %s
                         AND (gg.state = 'inprogress'
                              OR (gg.state = 'reached'
                                  AND (gg.end_date >= %s OR gg.end_date IS NULL)))
                      GROUP BY gg.id
        """, (tuple(self.ids), fields.Date.to_string(yesterday)))
        goal_ids = [res[0] for res in self.env.cr.fetchall()]
        # update every running goal already generated linked to selected challenges
        Goal.browse(goal_ids).update_goal()

        self._recompute_challenge_users()
        self._generate_goals_from_challenge()

        for challenge in self:
            if challenge.last_report_date != fields.Date.today():
                # goals closed but still opened at the last report date
                closed_goals_to_report = Goal.search([
                    ('challenge_id', '=', challenge.id),
                    ('start_date', '>=', challenge.last_report_date),
                    ('end_date', '<=', challenge.last_report_date)
                ])

                if challenge.next_report_date and fields.Date.from_string(fields.Date.today()) >= fields.Date.from_string(challenge.next_report_date):
                    challenge.report_progress()

                elif closed_goals_to_report.ids:
                    # some goals need a final report
                    challenge.report_progress(subset_goal_ids=closed_goals_to_report.ids)

        self.check_challenge_reward()
        return True

    def quick_update(self, cr, uid, challenge_id, context=None):
        """Update all the goals of a specific challenge, no generation of new goals"""
        goal_ids = self.pool.get('gamification.goal').search(cr, uid, [('challenge_id', '=', challenge_id)], context=context)
        self.pool.get('gamification.goal').update_goal(cr, uid, goal_ids, context=context)
        return True

    def _get_challenger_users(self, domain):
        return self.env['res.users'].search(eval(ustr(domain)))

    def _recompute_challenge_users(self):
        """Recompute the domain to add new users and remove the one no longer matching the domain"""
        for challenge in self:
            if challenge.user_domain:

                old_users = challenge.user_ids
                new_users = self._get_challenger_users(challenge.user_domain)
                to_remove = old_users - new_users
                to_add = new_users - old_users

                write_op = [(3, user.id) for user in to_remove]
                write_op += [(4, user.id) for user in to_add]
                if write_op:
                    challenge.write({'user_ids': write_op})

        return True

    ##### Automatic actions #####

    def _generate_goals_from_challenge(self):
        """Generate the goals for each line and user.

        If goals already exist for this line and user, the line is skipped. This
        can be called after each change in the list of users or lines.
        :param list(int) ids: the list of challenge concerned"""

        Goal = goal = self.env['gamification.goal']

        for challenge in self:
            (start_date, end_date) = start_end_date_for_period(challenge.period)

            # if no periodicity, use challenge dates
            if not start_date and challenge.start_date:
                start_date = challenge.start_date
            if not end_date and challenge.end_date:
                end_date = challenge.end_date

            for line in challenge.line_ids:

                # there is potentially a lot of users
                # detect the ones with no goal linked to this line
                date_clause = ""
                query_params = [line.id]
                if start_date:
                    date_clause += "AND g.start_date = %s"
                    query_params.append(start_date)
                if end_date:
                    date_clause += "AND g.end_date = %s"
                    query_params.append(end_date)
            
                query = """SELECT u.id AS user_id
                             FROM res_users u
                        LEFT JOIN gamification_goal g
                               ON (u.id = g.user_id)
                            WHERE line_id = %s
                              {date_clause}
                        """.format(date_clause=date_clause)

                self.env.cr.execute(query, query_params)
                user_with_goal_ids = self.env.cr.dictfetchall()

                participant_user_ids = challenge.user_ids.ids
                user_without_goal_ids = list(set(participant_user_ids) - set([user['user_id'] for user in user_with_goal_ids]))
                user_squating_challenge_ids = list(set([user['user_id'] for user in user_with_goal_ids]) - set(participant_user_ids))
                if user_squating_challenge_ids:
                    # users that used to match the challenge
                    Goal.search([('challenge_id', '=', challenge.id), ('user_id', 'in', user_squating_challenge_ids)]).unlink()

                values = {
                    'definition_id': line.definition_id.id,
                    'line_id': line.id,
                    'target_goal': line.target_goal,
                    'state': 'inprogress',
                }

                if start_date:
                    values['start_date'] = start_date
                if end_date:
                    values['end_date'] = end_date

                    # the goal is initialised over the limit to make sure we will compute it at least once
                    if line.condition == 'higher':
                        values['current'] = line.target_goal - 1
                    else:
                        values['current'] = line.target_goal + 1

                if challenge.remind_update_delay:
                    values['remind_update_delay'] = challenge.remind_update_delay

                for user_id in user_without_goal_ids:
                    values.update({'user_id': user_id})
                    goal += Goal.create(values)

            goal.update_goal()

        return True

    ##### JS utilities #####

    def _get_serialized_challenge_lines(self, user_id=False, restrict_goal_ids=False, restrict_top=False):
        """Return a serialised version of the goals information if the user has not completed every goal

        :challenge: browse record of challenge to compute
        :user_id: res.users id of the user retrieving progress (False if no distinction, only for ranking challenges)
        :restrict_goal_ids: <list(int)> compute only the results for this subset if gamification.goal ids, if False retrieve every goal of current running challenge
        :restrict_top: <int> for challenge lines where visibility_mode == 'ranking', retrieve only these bests results and itself, if False retrieve all
            restrict_goal_ids has priority over restrict_top

        format list
        # if visibility_mode == 'ranking'
        {
            'name': <gamification.goal.description name>,
            'description': <gamification.goal.description description>,
            'condition': <reach condition {lower,higher}>,
            'computation_mode': <target computation {manually,count,sum,python}>,
            'monetary': <{True,False}>,
            'suffix': <value suffix>,
            'action': <{True,False}>,
            'display_mode': <{progress,boolean}>,
            'target': <challenge line target>,
            'own_goal_id': <gamification.goal id where user_id == uid>,
            'goals': [
                {
                    'id': <gamification.goal id>,
                    'rank': <user ranking>,
                    'user_id': <res.users id>,
                    'name': <res.users name>,
                    'state': <gamification.goal state {draft,inprogress,reached,failed,canceled}>,
                    'completeness': <percentage>,
                    'current': <current value>,
                }
            ]
        },
        # if visibility_mode == 'personal'
        {
            'id': <gamification.goal id>,
            'name': <gamification.goal.description name>,
            'description': <gamification.goal.description description>,
            'condition': <reach condition {lower,higher}>,
            'computation_mode': <target computation {manually,count,sum,python}>,
            'monetary': <{True,False}>,
            'suffix': <value suffix>,
            'action': <{True,False}>,
            'display_mode': <{progress,boolean}>,
            'target': <challenge line target>,
            'state': <gamification.goal state {draft,inprogress,reached,failed,canceled}>,                                
            'completeness': <percentage>,
            'current': <current value>,
        }
        """
        Goal = self.env['gamification.goal']
        (start_date, end_date) = start_end_date_for_period(self.period)

        res_lines = []
        all_reached = True
        for line in self.line_ids:
            line_data = {
                'name': line.definition_id.name,
                'description': line.definition_id.description,
                'condition': line.definition_id.condition,
                'computation_mode': line.definition_id.computation_mode,
                'monetary': line.definition_id.monetary,
                'suffix': line.definition_id.suffix,
                'action': True if line.definition_id.action_id else False,
                'display_mode': line.definition_id.display_mode,
                'target': line.target_goal,
            }
            domain = [
                ('line_id', '=', line.id),
                ('state', '!=', 'draft'),
            ]
            if restrict_goal_ids:
                domain.append(('ids', 'in', restrict_goal_ids))
            else:
                # if no subset goals, use the dates for restriction
                if start_date:
                    domain.append(('start_date', '=', start_date))
                if end_date:
                    domain.append(('end_date', '=', end_date))

            if self.visibility_mode == 'personal':
                if not user_id:
                    raise UserError(_("Retrieving progress for personal challenge without user information"))
                domain.append(('user_id', '=', user_id))
                sorting = Goal._order
                limit = 1
            else:
                line_data.update({
                    'own_goal_id': False,
                    'goals': [],
                })
                sorting = "completeness desc, current desc"
                limit = False
            goals = Goal.search(domain, order=sorting, limit=limit)
            ranking = 0
            for goal in goals:
                if self.visibility_mode == 'personal':
                    # limit=1 so only one result
                    line_data.update({
                        'id': goal.id,
                        'current': goal.current,
                        'completeness': goal.completeness,
                        'state': goal.state,
                    })
                else:
                    ranking += 1
                    if user_id and goal.user_id.id == user_id:
                        line_data['own_goal_id'] = goal.id
                    elif restrict_top and ranking > restrict_top:
                        # not own goal and too low to be in top
                        continue

                    line_data['goals'].append({
                        'id': goal.id,
                        'user_id': goal.user_id.id,
                        'name': goal.user_id.name,
                        'rank': ranking,
                        'current': goal.current,
                        'completeness': goal.completeness,
                        'state': goal.state,
                    })
                if goal.state != 'reached':
                    all_reached = False
            if goals:
                res_lines.append(line_data)
        if all_reached:
            return []
        return res_lines

    ##### Reporting #####

    def report_progress(self, users=False, subset_goal_ids=False):
        """Post report about the progress of the goals

        :param challenge: the challenge object that need to be reported
        :param users: the list(res.users) of users that are concerned by
          the report. If False, will send the report to every user concerned
          (goal users and group that receive a copy). Only used for challenge with
          a visibility mode set to 'personal'.
        :param goal_ids: the list(int) of goal ids linked to the challenge for
          the report. If not specified, use the goals for the current challenge
          period. This parameter can be used to produce report for previous challenge
          periods.
        :param subset_goal_ids: a list(int) of goal ids to restrict the report
        """

        Temp = self.env['mail.template']
        if self.visibility_mode == 'ranking':
            lines_boards = self._get_serialized_challenge_lines(user_id=False, restrict_goal_ids=subset_goal_ids, restrict_top=False)

            body_html = Temp.with_context(challenge_lines=lines_boards).render_template(self.report_template_id.body_html, 'gamification.challenge', self.id)

            # send to every follower and participant of the challenge
            self.message_post(
                body=body_html,
                partner_ids=self.mapped('user_ids.partner_id').ids,
                subtype='mail.mt_comment')
            if self.report_message_group_id:
                self.report_message_group_id.message_post(
                    body=body_html,
                    subtype='mail.mt_comment')

        else:
            # generate individual reports
            for user in users or self.user_ids:
                goals = self._get_serialized_challenge_lines(user.id, restrict_goal_ids=subset_goal_ids)
                if not goals:
                    continue

                body_html = Temp.with_context(challenge_lines=goals).render_template(self.report_template_id.body_html, 'gamification.challenge', self.id)

                # send message only to users, not on the challenge
                self.message_post(
                    body=body_html,
                    partner_ids=[(4, user.partner_id.id)],
                    subtype='mail.mt_comment')
                if self.report_message_group_id:
                    self.report_message_group_id.message_post(
                        body=body_html,
                        subtype='mail.mt_comment')
        return self.write({'last_report_date': fields.Date.today()})

    ##### Challenges #####
    # TODO in trunk, remove unused parameter user_id
    def accept_challenge(self, cr, uid, challenge_ids, context=None, user_id=None):
        """The user accept the suggested challenge"""
        return self._accept_challenge(cr, uid, uid, challenge_ids, context=context)

    def _accept_challenge(self, cr, uid, user_id, challenge_ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, user_id, context=context)
        message = "%s has joined the challenge" % user.name
        self.message_post(cr, SUPERUSER_ID, challenge_ids, body=message, context=context)
        self.write(cr, SUPERUSER_ID, challenge_ids, {'invited_user_ids': [(3, user_id)], 'user_ids': [(4, user_id)]}, context=context)
        return self._generate_goals_from_challenge(cr, SUPERUSER_ID, challenge_ids, context=context)

    # TODO in trunk, remove unused parameter user_id
    def discard_challenge(self, cr, uid, challenge_ids, context=None, user_id=None):
        """The user discard the suggested challenge"""
        return self._discard_challenge(cr, uid, uid, challenge_ids, context=context)

    def _discard_challenge(self, cr, uid, user_id, challenge_ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, user_id, context=context)
        message = "%s has refused the challenge" % user.name
        self.message_post(cr, SUPERUSER_ID, challenge_ids, body=message, context=context)
        return self.write(cr, SUPERUSER_ID, challenge_ids, {'invited_user_ids': (3, user_id)}, context=context)

    def reply_challenge_wizard(self, cr, uid, challenge_id, context=None):
        result = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'gamification', 'challenge_wizard')
        id = result and result[1] or False
        result = self.pool.get('ir.actions.act_window').read(cr, uid, [id], context=context)[0]
        result['res_id'] = challenge_id
        return result

    def check_challenge_reward(self, force=False):
        """Actions for the end of a challenge

        If a reward was selected, grant it to the correct users.
        Rewards granted at:
            - the end date for a challenge with no periodicity
            - the end of a period for challenge with periodicity
            - when a challenge is manually closed
        (if no end date, a running challenge is never rewarded)
        """
        commit = self.env.context.get('commit_gamification', False)
        for challenge in self:
            (start_date, end_date) = start_end_date_for_period(challenge.period, challenge.start_date, challenge.end_date)
            yesterday = fields.Date.from_string(fields.Date.today()) - timedelta(days=1)

            rewarded_users = []
            challenge_ended = end_date == fields.Date.to_string(yesterday) or force
            if challenge.reward_id and (challenge_ended or challenge.reward_realtime):
                # not using start_date as intemportal goals have a start date but no end_date
                reached_goals = self.env['gamification.goal'].read_group([
                    ('challenge_id', '=', challenge.id),
                    ('end_date', '=', end_date),
                    ('state', '=', 'reached')
                ], fields=['user_id'], groupby=['user_id'])
                for reach_goals_user in reached_goals:
                    if reach_goals_user['user_id_count'] == len(challenge.line_ids):
                        # the user has succeeded every assigned goal
                        user_id = reach_goals_user['user_id'][0]
                        if challenge.reward_realtime:
                            badges = self.env['gamification.badge.user'].search_count([
                                ('challenge_id', '=', challenge.id),
                                ('badge_id', '=', challenge.reward_id.id),
                                ('user_id', '=', user_id),
                            ])
                            if badges > 0:
                                # has already recieved the badge for this challenge
                                continue
                        self.reward_user(user_id, challenge.reward_id.id, challenge.id)
                        rewarded_users.append(user_id)
                        if commit:
                            self.env.cr.commit()

            if challenge_ended:
                # open chatter message
                message_body = _("The challenge %s is finished.") % challenge.name

                if rewarded_users:
                    user_names = self.env['res.users'].browse(rewarded_users).name_get()
                    message_body += _("<br/>Reward (badge %s) for every succeeding user was sent to %s." % (challenge.reward_id.name, ", ".join([name for (user_id, name) in user_names])))
                else:
                    message_body += _("<br/>Nobody has succeeded to reach every goal, no badge is rewarded for this challenge.")

                # reward bests
                if challenge.reward_first_id:
                    (first_user, second_user, third_user) = challenge.get_top3_users()
                    if first_user:
                        self.reward_user(first_user.id, challenge.reward_first_id.id, challenge.id)
                        message_body += _("<br/>Special rewards were sent to the top competing users. The ranking for this challenge is :")
                        message_body += "<br/> 1. %s - %s" % (first_user.name, challenge.reward_first_id.name)
                    else:
                        message_body += _("Nobody reached the required conditions to receive special badges.")

                    if second_user and challenge.reward_second_id:
                        self.reward_user(second_user.id, challenge.reward_second_id.id, challenge.id)
                        message_body += "<br/> 2. %s - %s" % (second_user.name, challenge.reward_second_id.name)
                    if third_user and challenge.reward_third_id:
                        self.reward_user(third_user.id, challenge.reward_second_id.id, challenge.id)
                        message_body += "<br/> 3. %s - %s" % (third_user.name, challenge.reward_third_id.name)

                challenge.message_post(
                    partner_ids=[user.partner_id.id for user in challenge.user_ids],
                    body=message_body)
                if commit:
                    self.env.cr.commit()

        return True

    def get_top3_users(self):
        """Get the top 3 users for a defined challenge

        Ranking criterias:
            1. succeed every goal of the challenge
            2. total completeness of each goal (can be over 100)
        Top 3 is computed only for users succeeding every goal of the challenge,
        except if reward_failure is True, in which case every user is
        considered.
        :return: ('first', 'second', 'third'), tuple containing the res.users
        objects of the top 3 users. If no user meets the criterias for a rank,
        it is set to False. Nobody can receive a rank is noone receives the
        higher one (eg: if 'second' == False, 'third' will be False)
        """
        Goal = self.env['gamification.goal']
        (start_date, end_date) = start_end_date_for_period(self.period, self.start_date, self.end_date)
        challengers = []
        for user in self.user_ids:
            all_reached = True
            total_completness = 0
            # every goal of the user for the running period
            goals = Goal.search([
                ('challenge_id', '=', self.id),
                ('user_id', '=', user.id),
                ('start_date', '=', start_date),
                ('end_date', '=', end_date)
            ])
            for goal in goals:
                if goal.state != 'reached':
                    all_reached = False
                if goal.definition_condition == 'higher':
                    # can be over 100
                    total_completness += 100.0 * goal.current / goal.target_goal
                elif goal.state == 'reached':
                    # for lower goals, can not get percentage so 0 or 100
                    total_completness += 100

            challengers.append({'user': user, 'all_reached': all_reached, 'total_completness': total_completness})
        sorted_challengers = sorted(challengers, key=lambda k: (k['all_reached'], k['total_completness']), reverse=True)

        if len(sorted_challengers) == 0 or (not self.reward_failure and not sorted_challengers[0]['all_reached']):
            # nobody succeeded
            return (False, False, False)
        if len(sorted_challengers) == 1 or (not self.reward_failure and not sorted_challengers[1]['all_reached']):
            # only one user succeeded
            return (sorted_challengers[0]['user'], False, False)
        if len(sorted_challengers) == 2 or (not self.reward_failure and not sorted_challengers[2]['all_reached']):
            # only one user succeeded
            return (sorted_challengers[0]['user'], sorted_challengers[1]['user'], False)
        return (sorted_challengers[0]['user'], sorted_challengers[1]['user'], sorted_challengers[2]['user'])

    def reward_user(self, user_id, badge_id, challenge_id=False):
        """Create a badge user and send the badge to him

        :param user_id: the user to reward
        :param badge_id: the concerned badge
        """
        return self.env['gamification.badge.user'].create({'user_id': user_id, 'badge_id': badge_id, 'challenge_id': challenge_id})._send_badge()


class GamificationChallengeLine(models.Model):
    """Gamification challenge line

    Predifined goal for 'gamification_challenge'
    These are generic list of goals with only the target goal defined
    Should only be created for the gamification_challenge object
    """

    _name = 'gamification.challenge.line'
    _description = 'Gamification generic goal for challenge'
    _order = "sequence, id"

    name = fields.Char(related='definition_id.name')
    challenge_id = fields.Many2one(
        'gamification.challenge',
        string='Challenge', required=True, ondelete="cascade")
    definition_id = fields.Many2one(
        'gamification.goal.definition', string='Goal Definition',
        required=True, ondelete="cascade")
    target_goal = fields.Float(string='Target Value to Reach', required=True)
    sequence = fields.Integer(help='Sequence number for ordering', default=1)
    condition = fields.Selection(
        related='definition_id.condition',
        readonly=True, selection=[('lower', '<='), ('higher', '>=')])
    definition_suffix = fields.Char(related='definition_id.suffix', readonly=True, string="Unit")
    definition_monetary = fields.Boolean(related='definition_id.monetary', readonly=True, string="Monetary")
    definition_full_suffix = fields.Char(related='definition_id.full_suffix', readonly=True, string="Suffix")

    @api.onchange("definition_id")
    def on_change_definition_id(self):
        self.condition = self.definition_id.condition
        self.definition_full_suffix = self.definition_id.full_suffix
