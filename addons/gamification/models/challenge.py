# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import itertools
import logging
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta, MO

from odoo import api, models, fields, _, exceptions
from odoo.tools import ustr
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

# display top 3 in ranking, could be db variable
MAX_VISIBILITY_RANKING = 3

def start_end_date_for_period(period, default_start_date=False, default_end_date=False):
    """Return the start and end date for a goal period based on today

    :param str default_start_date: string date in DEFAULT_SERVER_DATE_FORMAT format
    :param str default_end_date: string date in DEFAULT_SERVER_DATE_FORMAT format

    :return: (start_date, end_date), dates in string format, False if the period is
    not defined or unknown"""
    today = date.today()
    if period == 'daily':
        start_date = today
        end_date = start_date
    elif period == 'weekly':
        start_date = today + relativedelta(weekday=MO(-1))
        end_date = start_date + timedelta(days=7)
    elif period == 'monthly':
        start_date = today.replace(day=1)
        end_date = today + relativedelta(months=1, day=1, days=-1)
    elif period == 'yearly':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
    else:  # period == 'once':
        start_date = default_start_date  # for manual goal, start each time
        end_date = default_end_date

        return (start_date, end_date)

    return fields.Datetime.to_string(start_date), fields.Datetime.to_string(end_date)

class Challenge(models.Model):
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

    name = fields.Char("Challenge Name", required=True, translate=True)
    description = fields.Text("Description", translate=True)
    state = fields.Selection([
            ('draft', "Draft"),
            ('inprogress', "In Progress"),
            ('done', "Done"),
        ], default='draft', copy=False,
        string="State", required=True, track_visibility='onchange')
    manager_id = fields.Many2one(
        'res.users', default=lambda self: self.env.uid,
        string="Responsible", help="The user responsible for the challenge.",)

    user_ids = fields.Many2many('res.users', 'gamification_challenge_users_rel', string="Users", help="List of users participating to the challenge")
    user_domain = fields.Char("User domain", help="Alternative to a list of users")

    period = fields.Selection([
            ('once', "Non recurring"),
            ('daily', "Daily"),
            ('weekly', "Weekly"),
            ('monthly', "Monthly"),
            ('yearly', "Yearly")
        ], default='once',
        string="Periodicity",
        help="Period of automatic goal assigment. If none is selected, should be launched manually.",
        required=True)
    start_date = fields.Date("Start Date", help="The day a new challenge will be automatically started. If no periodicity is set, will use this date as the goal start date.")
    end_date = fields.Date("End Date", help="The day a new challenge will be automatically closed. If no periodicity is set, will use this date as the goal end date.")

    invited_user_ids = fields.Many2many('res.users', 'gamification_invited_user_ids_rel', string="Suggest to users")

    line_ids = fields.One2many('gamification.challenge.line', 'challenge_id',
                                  string="Lines",
                                  help="List of goals that will be set",
                                  required=True, copy=True)

    reward_id = fields.Many2one('gamification.badge', string="For Every Succeeding User")
    reward_first_id = fields.Many2one('gamification.badge', string="For 1st user")
    reward_second_id = fields.Many2one('gamification.badge', string="For 2nd user")
    reward_third_id = fields.Many2one('gamification.badge', string="For 3rd user")
    reward_failure = fields.Boolean("Reward Bests if not Succeeded?")
    reward_realtime = fields.Boolean("Reward as soon as every goal is reached", default=True, help="With this option enabled, a user can receive a badge only once. The top 3 badges are still rewarded only at the end of the challenge.")

    visibility_mode = fields.Selection([
            ('personal', "Individual Goals"),
            ('ranking', "Leader Board (Group Ranking)"),
        ], default='personal',
        string="Display Mode", required=True)

    report_message_frequency = fields.Selection([
            ('never', "Never"),
            ('onchange', "On change"),
            ('daily', "Daily"),
            ('weekly', "Weekly"),
            ('monthly', "Monthly"),
            ('yearly', "Yearly")
        ], default='never',
        string="Report Frequency", required=True)
    report_message_group_id = fields.Many2one('mail.channel', string="Send a copy to", help="Group that will receive a copy of the report in addition to the user")
    report_template_id = fields.Many2one('mail.template', default=lambda self: self._get_report_template(), string="Report Template", required=True)
    remind_update_delay = fields.Integer("Non-updated manual goals will be reminded after", help="Never reminded if no value or zero is specified.")
    last_report_date = fields.Date("Last Report Date", default=fields.Date.today)
    next_report_date = fields.Date("Next Report Date", compute='_get_next_report_date', store=True)

    category = fields.Selection([
        ('hr', 'Human Resources / Engagement'),
        ('other', 'Settings / Gamification Tools'),
    ], string="Appears in", required=True, default='hr',
       help="Define the visibility of the challenge through menus")

    REPORT_OFFSETS = {
        'daily': timedelta(days=1),
        'weekly': timedelta(days=7),
        'monthly': relativedelta(months=1),
        'yearly': relativedelta(years=1),
    }
    @api.depends('last_report_date', 'report_message_frequency')
    def _get_next_report_date(self):
        """ Return the next report date based on the last report date and
        report period.
        """
        for challenge in self:
            last = fields.Datetime.from_string(challenge.last_report_date).date()
            offset = self.REPORT_OFFSETS.get(challenge.report_message_frequency)

            if offset:
                challenge.next_report_date = fields.Date.to_string(last + offset)
            else:
                challenge.next_report_date = False

    def _get_report_template(self):
        template = self.env.ref('gamification.simple_report_template', raise_if_not_found=False)

        return template.id if template else False

    @api.model
    def create(self, vals):
        """Overwrite the create method to add the user of groups"""

        if vals.get('user_domain'):
            users = self._get_challenger_users(ustr(vals.get('user_domain')))

            if not vals.get('user_ids'):
                vals['user_ids'] = []
            vals['user_ids'].extend((4, user.id) for user in users)

        return super(Challenge, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('user_domain'):
            users = self._get_challenger_users(ustr(vals.get('user_domain')))

            if not vals.get('user_ids'):
                vals['user_ids'] = []
            vals['user_ids'].extend((4, user.id) for user in users)

        write_res = super(Challenge, self).write(vals)

        if vals.get('report_message_frequency', 'never') != 'never':
            # _recompute_challenge_users do not set users for challenges with no reports, subscribing them now
            for challenge in self:
                challenge.message_subscribe([user.partner_id.id for user in challenge.user_ids])

        if vals.get('state') == 'inprogress':
            self._recompute_challenge_users()
            self._generate_goals_from_challenge()

        elif vals.get('state') == 'done':
            self._check_challenge_reward(force=True)

        elif vals.get('state') == 'draft':
            # resetting progress
            if self.env['gamification.goal'].search([('challenge_id', 'in', self.ids), ('state', '=', 'inprogress')], limit=1):
                raise exceptions.UserError(_("You can not reset a challenge with unfinished goals."))

        return write_res


    ##### Update #####

    @api.model # FIXME: check how cron functions are called to see if decorator necessary
    def _cron_update(self, ids=False):
        """Daily cron check.

        - Start planned challenges (in draft and with start_date = today)
        - Create the missing goals (eg: modified the challenge to add lines)
        - Update every running challenge
        """
        # start scheduled challenges
        planned_challenges = self.search([
            ('state', '=', 'draft'),
            ('start_date', '<=', fields.Date.today())
        ])
        if planned_challenges:
            planned_challenges.write({'state': 'inprogress'})

        # close scheduled challenges
        scheduled_challenges = self.search([
            ('state', '=', 'inprogress'),
            ('end_date', '<', fields.Date.today())
        ])
        if scheduled_challenges:
            scheduled_challenges.write({'state': 'done'})

        records = self.browse(ids) if ids else self.search([('state', '=', 'inprogress')])

        # in cron mode, will do intermediate commits
        # FIXME: replace by parameter
        return records.with_context(commit_gamification=True)._update_all()

    def _update_all(self):
        """Update the challenges and related goals

        :param list(int) ids: the ids of the challenges to update, if False will
        update only challenges in progress."""
        if not self:
            return True

        Goals = self.env['gamification.goal']

        # include yesterday goals to update the goals that just ended
        # exclude goals for users that did not connect since the last update
        yesterday = fields.Date.to_string(date.today() - timedelta(days=1))
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
        """, [tuple(self.ids), yesterday])

        Goals.browse(goal_id for [goal_id] in self.env.cr.fetchall()).update_goal()

        self._recompute_challenge_users()
        self._generate_goals_from_challenge()

        for challenge in self:
            if challenge.last_report_date != fields.Date.today():
                # goals closed but still opened at the last report date
                closed_goals_to_report = Goals.search([
                    ('challenge_id', '=', challenge.id),
                    ('start_date', '>=', challenge.last_report_date),
                    ('end_date', '<=', challenge.last_report_date)
                ])

                if challenge.next_report_date and fields.Date.today() >= challenge.next_report_date:
                    challenge.report_progress()
                elif closed_goals_to_report:
                    # some goals need a final report
                    challenge.report_progress(subset_goals=closed_goals_to_report)

        self._check_challenge_reward()
        return True

    def _get_challenger_users(self, domain):
        # FIXME: literal_eval?
        user_domain = safe_eval(domain)
        return self.env['res.users'].search(user_domain)

    def _recompute_challenge_users(self):
        """Recompute the domain to add new users and remove the one no longer matching the domain"""
        for challenge in self.filtered(lambda c: c.user_domain):
            current_users = challenge.user_ids
            new_users = self._get_challenger_users(challenge.user_domain)

            if current_users != new_users:
                challenge.user_ids = new_users

        return True

    @api.multi
    def action_start(self):
        """Start a challenge"""
        return self.write({'state': 'inprogress'})

    @api.multi
    def action_check(self):
        """Check a challenge

        Create goals that haven't been created yet (eg: if added users)
        Recompute the current value for each goal related"""
        self.env['gamification.goal'].search([
            ('challenge_id', 'in', self.ids),
            ('state', '=', 'inprogress')
        ]).unlink()

        return self._update_all()

    @api.multi
    def action_report_progress(self):
        """Manual report of a goal, does not influence automatic report frequency"""
        for challenge in self:
            challenge.report_progress()
        return True

    ##### Automatic actions #####

    def _generate_goals_from_challenge(self):
        """Generate the goals for each line and user.

        If goals already exist for this line and user, the line is skipped. This
        can be called after each change in the list of users or lines.
        :param list(int) ids: the list of challenge concerned"""

        Goals = self.env['gamification.goal']
        for challenge in self:
            (start_date, end_date) = start_end_date_for_period(challenge.period, challenge.start_date, challenge.end_date)
            to_update = Goals.browse(())

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
                user_with_goal_ids = {it for [it] in self.env.cr._obj}

                participant_user_ids = set(challenge.user_ids.ids)
                user_squating_challenge_ids = user_with_goal_ids - participant_user_ids
                if user_squating_challenge_ids:
                    # users that used to match the challenge 
                    Goals.search([
                        ('challenge_id', '=', challenge.id),
                        ('user_id', 'in', list(user_squating_challenge_ids))
                    ]).unlink()

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

                for user_id in (participant_user_ids - user_with_goal_ids):
                    values['user_id'] = user_id
                    to_update |= Goals.create(values)

            to_update.update_goal()

        return True

    ##### JS utilities #####

    def _get_serialized_challenge_lines(self, user=(), restrict_goals=(), restrict_top=0):
        """Return a serialised version of the goals information if the user has not completed every goal

        :param user: user retrieving progress (False if no distinction,
                     only for ranking challenges)
        :param restrict_goals: compute only the results for this subset of
                               gamification.goal ids, if False retrieve every
                               goal of current running challenge
        :param int restrict_top: for challenge lines where visibility_mode is
                                 ``ranking``, retrieve only the best
                                 ``restrict_top`` results and itself, if 0
                                 retrieve all restrict_goal_ids has priority
                                 over restrict_top

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
        Goals = self.env['gamification.goal']
        (start_date, end_date) = start_end_date_for_period(self.period)

        res_lines = []
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
            if restrict_goals:
                domain.append(('ids', 'in', restrict_goals.ids))
            else:
                # if no subset goals, use the dates for restriction
                if start_date:
                    domain.append(('start_date', '=', start_date))
                if end_date:
                    domain.append(('end_date', '=', end_date))

            if self.visibility_mode == 'personal':
                if not user:
                    raise exceptions.UserError(_("Retrieving progress for personal challenge without user information"))

                domain.append(('user_id', '=', user.id))

                goal = Goals.search(domain, limit=1)
                if not goal:
                    continue

                if goal.state != 'reached':
                    return []
                line_data.update(goal.read(['id', 'current', 'completeness', 'state'])[0])
                res_lines.append(line_data)
                continue

            line_data['own_goal_id'] = False,
            line_data['goals'] = []
            if line.condition=='higher':
                goals = Goals.search(domain, order="completeness desc, current desc")
            else:
                goals = Goals.search(domain, order="completeness desc, current asc")
            for ranking, goal in enumerate(goals):
                if user and goal.user_id == user:
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
            if goals:
                res_lines.append(line_data)
        return res_lines

    ##### Reporting #####

    def report_progress(self, users=(), subset_goals=False):
        """Post report about the progress of the goals

        :param users: users that are concerned by the report. If False, will
                      send the report to every user concerned (goal users and
                      group that receive a copy). Only used for challenge with
                      a visibility mode set to 'personal'.
        :param subset_goals: goals to restrict the report
        """

        challenge = self

        MailTemplates = self.env['mail.template']
        if challenge.visibility_mode == 'ranking':
            lines_boards = challenge._get_serialized_challenge_lines(restrict_goals=subset_goals)

            body_html = MailTemplates.with_context(challenge_lines=lines_boards).render_template(challenge.report_template_id.body_html, 'gamification.challenge', challenge.id)

            # send to every follower and participant of the challenge
            challenge.message_post(
                body=body_html,
                partner_ids=challenge.mapped('user_ids.partner_id.id'),
                subtype='mail.mt_comment')
            if challenge.report_message_group_id:
                challenge.report_message_group_id.message_post(
                    body=body_html,
                    subtype='mail.mt_comment')

        else:
            # generate individual reports
            for user in (users or challenge.user_ids):
                lines = challenge._get_serialized_challenge_lines(user, restrict_goals=subset_goals)
                if not lines:
                    continue

                body_html = MailTemplates.sudo(user).with_context(challenge_lines=lines).render_template(
                    challenge.report_template_id.body_html,
                    'gamification.challenge',
                    challenge.id)

                # send message only to users, not on the challenge
                self.env['gamification.challenge'].message_post(
                    body=body_html,
                    partner_ids=[(4, user.partner_id.id)],
                    subtype='mail.mt_comment'
                )
                if challenge.report_message_group_id:
                    challenge.report_message_group_id.message_post(
                         body=body_html,
                         subtype='mail.mt_comment')
        return challenge.write({'last_report_date': fields.Date.today()})

    ##### Challenges #####
    @api.multi
    def accept_challenge(self):
        user = self.env.user
        sudoed = self.sudo()
        sudoed.message_post(body=_("%s has joined the challenge") % user.name)
        sudoed.write({'invited_user_ids': [(3, user.id)], 'user_ids': [(4, user.id)]})
        return sudoed._generate_goals_from_challenge()

    @api.multi
    def discard_challenge(self):
        """The user discard the suggested challenge"""
        user = self.env.user
        sudoed = self.sudo()
        sudoed.message_post(body=_("%s has refused the challenge") % user.name)
        return sudoed.write({'invited_user_ids': (3, user.id)})

    def _check_challenge_reward(self, force=False):
        """Actions for the end of a challenge

        If a reward was selected, grant it to the correct users.
        Rewards granted at:
            - the end date for a challenge with no periodicity
            - the end of a period for challenge with periodicity
            - when a challenge is manually closed
        (if no end date, a running challenge is never rewarded)
        """
        commit = self.env.context.get('commit_gamification') and self.env.cr.commit

        for challenge in self:
            (start_date, end_date) = start_end_date_for_period(challenge.period, challenge.start_date, challenge.end_date)
            yesterday = date.today() - timedelta(days=1)

            rewarded_users = self.env['res.users']
            challenge_ended = force or end_date == fields.Date.to_string(yesterday)
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
                        user = self.env['res.users'].browse(reach_goals_user['user_id'][0])
                        if challenge.reward_realtime:
                            badges = self.env['gamification.badge.user'].search_count([
                                ('challenge_id', '=', challenge.id),
                                ('badge_id', '=', challenge.reward_id.id),
                                ('user_id', '=', user.id),
                            ])
                            if badges > 0:
                                # has already recieved the badge for this challenge
                                continue
                        challenge._reward_user(user, challenge.reward_id)
                        rewarded_users |= user
                        if commit:
                            commit()

            if challenge_ended:
                # open chatter message
                message_body = _("The challenge %s is finished.") % challenge.name

                if rewarded_users:
                    user_names = rewarded_users.name_get()
                    message_body += _("<br/>Reward (badge %s) for every succeeding user was sent to %s.") % (challenge.reward_id.name, ", ".join(name for (user_id, name) in user_names))
                else:
                    message_body += _("<br/>Nobody has succeeded to reach every goal, no badge is rewarded for this challenge.")

                # reward bests
                reward_message = _("<br/> %(rank)d. %(user_name)s - %(reward_name)s")
                if challenge.reward_first_id:
                    (first_user, second_user, third_user) = challenge._get_topN_users(MAX_VISIBILITY_RANKING)
                    if first_user:
                        challenge._reward_user(first_user, challenge.reward_first_id)
                        message_body += _("<br/>Special rewards were sent to the top competing users. The ranking for this challenge is :")
                        message_body += reward_message % {
                            'rank': 1,
                            'user_name': first_user.name,
                            'reward_name': challenge.reward_first_id.name,
                        }
                    else:
                        message_body += _("Nobody reached the required conditions to receive special badges.")

                    if second_user and challenge.reward_second_id:
                        challenge._reward_user(second_user, challenge.reward_second_id)
                        message_body += reward_message % {
                            'rank': 2,
                            'user_name': second_user.name,
                            'reward_name': challenge.reward_second_id.name,
                        }
                    if third_user and challenge.reward_third_id:
                        challenge._reward_user(third_user, challenge.reward_third_id)
                        message_body += reward_message % {
                            'rank': 3,
                            'user_name': third_user.name,
                            'reward_name': challenge.reward_third_id.name,
                        }

                challenge.message_post(
                    partner_ids=[user.partner_id.id for user in challenge.user_ids],
                    body=message_body)
                if commit:
                    commit()

        return True

    def _get_topN_users(self, n):
        """Get the top N users for a defined challenge

        Ranking criterias:
            1. succeed every goal of the challenge
            2. total completeness of each goal (can be over 100)

        Only users having reached every goal of the challenge will be returned
        unless the challenge ``reward_failure`` is set, in which case any user
        may be considered.

        :returns: an iterable of exactly N records, either User objects or
                  False if there was no user for the rank. There can be no
                  False between two users (if users[k] = False then
                  users[k+1] = False
        """
        Goals = self.env['gamification.goal']
        (start_date, end_date) = start_end_date_for_period(self.period, self.start_date, self.end_date)
        challengers = []
        for user in self.user_ids:
            all_reached = True
            total_completeness = 0
            # every goal of the user for the running period
            goal_ids = Goals.search([
                ('challenge_id', '=', self.id),
                ('user_id', '=', user.id),
                ('start_date', '=', start_date),
                ('end_date', '=', end_date)
            ])
            for goal in goal_ids:
                if goal.state != 'reached':
                    all_reached = False
                if goal.definition_condition == 'higher':
                    # can be over 100
                    total_completeness += 100.0 * goal.current / goal.target_goal
                elif goal.state == 'reached':
                    # for lower goals, can not get percentage so 0 or 100
                    total_completeness += 100

            challengers.append({'user': user, 'all_reached': all_reached, 'total_completeness': total_completeness})

        challengers.sort(key=lambda k: (k['all_reached'], k['total_completeness']), reverse=True)
        if not self.reward_failure:
            # only keep the fully successful challengers at the front, could
            # probably use filter since the successful ones are at the front
            challengers = itertools.takewhile(lambda c: c['all_reached'], challengers)

        # append a tail of False, then keep the first N
        challengers = itertools.islice(
            itertools.chain(
                (c['user'] for c in challengers),
                itertools.repeat(False),
            ), 0, n
        )

        return tuple(challengers)

    def _reward_user(self, user, badge):
        """Create a badge user and send the badge to him

        :param user: the user to reward
        :param badge: the concerned badge
        """
        return self.env['gamification.badge.user'].create({
            'user_id': user.id,
            'badge_id': badge.id,
            'challenge_id': self.id
        })._send_badge()


class ChallengeLine(models.Model):
    """Gamification challenge line

    Predefined goal for 'gamification_challenge'
    These are generic list of goals with only the target goal defined
    Should only be created for the gamification.challenge object
    """
    _name = 'gamification.challenge.line'
    _description = 'Gamification generic goal for challenge'
    _order = "sequence, id"

    challenge_id = fields.Many2one('gamification.challenge', string='Challenge', required=True, ondelete="cascade")
    definition_id = fields.Many2one('gamification.goal.definition', string='Goal Definition', required=True, ondelete="cascade")

    sequence = fields.Integer('Sequence', help='Sequence number for ordering', default=1)
    target_goal = fields.Float('Target Value to Reach', required=True)

    name = fields.Char("Name", related='definition_id.name')
    condition = fields.Selection("Condition", related='definition_id.condition', readonly=True)
    definition_suffix = fields.Char("Unit", related='definition_id.suffix', readonly=True)
    definition_monetary = fields.Boolean("Monetary", related='definition_id.monetary', readonly=True)
    definition_full_suffix = fields.Char("Suffix", related='definition_id.full_suffix', readonly=True)
