# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from openerp.tools.translate import _

from datetime import date, datetime, timedelta
import calendar
import logging
_logger = logging.getLogger(__name__)

# display top 3 in ranking, could be db variable
MAX_VISIBILITY_RANKING = 3

def start_end_date_for_period(period, default_start_date=False, default_end_date=False):
    """Return the start and end date for a goal period based on today

    :return: (start_date, end_date), datetime.date objects, False if the period is
    not defined or unknown"""
    today = date.today()
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
        start_date = default_start_date  # for manual goal, start each time
        end_date = default_end_date

    if start_date and end_date:
        return (datetime.strftime(start_date, DF), datetime.strftime(end_date, DF))
    else:
        return (start_date, end_date)


class gamification_challenge(osv.Model):
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

    def _get_next_report_date(self, cr, uid, ids, field_name, arg, context=None):
        """Return the next report date based on the last report date and report
        period.

        :return: a string in DEFAULT_SERVER_DATE_FORMAT representing the date"""
        res = {}
        for challenge in self.browse(cr, uid, ids, context):
            last = datetime.strptime(challenge.last_report_date, DF).date()
            if challenge.report_message_frequency == 'daily':
                next = last + timedelta(days=1)
                res[challenge.id] = next.strftime(DF)
            elif challenge.report_message_frequency == 'weekly':
                next = last + timedelta(days=7)
                res[challenge.id] = next.strftime(DF)
            elif challenge.report_message_frequency == 'monthly':
                month_range = calendar.monthrange(last.year, last.month)
                next = last.replace(day=month_range[1]) + timedelta(days=1)
                res[challenge.id] = next.strftime(DF)
            elif challenge.report_message_frequency == 'yearly':
                res[challenge.id] = last.replace(year=last.year + 1).strftime(DF)
            # frequency == 'once', reported when closed only
            else:
                res[challenge.id] = False

        return res
    
    def _get_categories(self, cr, uid, context=None):
        return [
            ('hr', 'Human Ressources / Engagement'),
            ('other', 'Settings / Gamification Tools'),
        ]

    def _get_report_template(self, cr, uid, context=None):
        try:
            return self.pool.get('ir.model.data').get_object_reference(cr, uid, 'gamification', 'simple_report_template')[1]
        except ValueError:
            return False

    _order = 'end_date, start_date, name, id'
    _columns = {
        'name': fields.char('Challenge Name', required=True, translate=True),
        'description': fields.text('Description', translate=True),
        'state': fields.selection([
                ('draft', 'Draft'),
                ('inprogress', 'In Progress'),
                ('done', 'Done'),
            ],
            string='State', required=True, track_visibility='onchange'),
        'manager_id': fields.many2one('res.users',
            string='Responsible', help="The user responsible for the challenge."),

        'user_ids': fields.many2many('res.users', 'user_ids',
            string='Users',
            help="List of users participating to the challenge"),
        'autojoin_group_id': fields.many2one('res.groups',
            string='Auto-subscription Group',
            help='Group of users whose members will be automatically added to user_ids once the challenge is started'),

        'period': fields.selection([
                ('once', 'Non recurring'),
                ('daily', 'Daily'),
                ('weekly', 'Weekly'),
                ('monthly', 'Monthly'),
                ('yearly', 'Yearly')
            ],
            string='Periodicity',
            help='Period of automatic goal assigment. If none is selected, should be launched manually.',
            required=True),
        'start_date': fields.date('Start Date',
            help="The day a new challenge will be automatically started. If no periodicity is set, will use this date as the goal start date."),
        'end_date': fields.date('End Date',
            help="The day a new challenge will be automatically closed. If no periodicity is set, will use this date as the goal end date."),

        'invited_user_ids': fields.many2many('res.users', 'invited_user_ids',
            string="Suggest to users"),

        'line_ids': fields.one2many('gamification.challenge.line', 'challenge_id',
            string='Lines',
            help="List of goals that will be set",
            required=True),

        'reward_id': fields.many2one('gamification.badge', string="For Every Succeding User"),
        'reward_first_id': fields.many2one('gamification.badge', string="For 1st user"),
        'reward_second_id': fields.many2one('gamification.badge', string="For 2nd user"),
        'reward_third_id': fields.many2one('gamification.badge', string="For 3rd user"),
        'reward_failure': fields.boolean('Reward Bests if not Succeeded?'),

        'visibility_mode': fields.selection([
                ('personal', 'Individual Goals'),
                ('ranking', 'Leader Board (Group Ranking)'),
            ],
            string="Display Mode", required=True),

        'report_message_frequency': fields.selection([
                ('never', 'Never'),
                ('onchange', 'On change'),
                ('daily', 'Daily'),
                ('weekly', 'Weekly'),
                ('monthly', 'Monthly'),
                ('yearly', 'Yearly')
            ],
            string="Report Frequency", required=True),
        'report_message_group_id': fields.many2one('mail.group',
            string='Send a copy to',
            help='Group that will receive a copy of the report in addition to the user'),
        'report_template_id': fields.many2one('email.template', string="Report Template", required=True),
        'remind_update_delay': fields.integer('Non-updated manual goals will be reminded after',
            help="Never reminded if no value or zero is specified."),
        'last_report_date': fields.date('Last Report Date'),
        'next_report_date': fields.function(_get_next_report_date,
            type='date', string='Next Report Date', store=True),

        'category': fields.selection(lambda s, *a, **k: s._get_categories(*a, **k),
            string="Appears in", help="Define the visibility of the challenge through menus", required=True),
        }

    _defaults = {
        'period': 'once',
        'state': 'draft',
        'visibility_mode': 'personal',
        'report_message_frequency': 'never',
        'last_report_date': fields.date.today,
        'manager_id': lambda s, cr, uid, c: uid,
        'category': 'hr',
        'reward_failure': False,
        'report_template_id': lambda s, *a, **k: s._get_report_template(*a, **k),
    }


    def create(self, cr, uid, vals, context=None):
        """Overwrite the create method to add the user of groups"""

        # add users when change the group auto-subscription
        if vals.get('autojoin_group_id'):
            new_group = self.pool.get('res.groups').browse(cr, uid, vals['autojoin_group_id'], context=context)

            if not vals.get('user_ids'):
                vals['user_ids'] = []
            vals['user_ids'] += [(4, user.id) for user in new_group.users]

        create_res = super(gamification_challenge, self).create(cr, uid, vals, context=context)

        # subscribe new users to the challenge
        if vals.get('user_ids'):
            # done with browse after super to be sure catch all after orm process
            challenge = self.browse(cr, uid, create_res, context=context)
            self.message_subscribe_users(cr, uid, [challenge.id], [user.id for user in challenge.user_ids], context=context)

        return create_res

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int,long)):
            ids = [ids]

        # add users when change the group auto-subscription
        if vals.get('autojoin_group_id'):
            new_group = self.pool.get('res.groups').browse(cr, uid, vals['autojoin_group_id'], context=context)

            if not vals.get('user_ids'):
                vals['user_ids'] = []
            vals['user_ids'] += [(4, user.id) for user in new_group.users]

        if vals.get('state') == 'inprogress':
            # starting a challenge
            if not vals.get('autojoin_group_id'):
                # starting challenge, add users in autojoin group
                if not vals.get('user_ids'):
                    vals['user_ids'] = []
                for challenge in self.browse(cr, uid, ids, context=context):
                    if challenge.autojoin_group_id:
                        vals['user_ids'] += [(4, user.id) for user in challenge.autojoin_group_id.users]

            self.generate_goals_from_challenge(cr, uid, ids, context=context)

        elif vals.get('state') == 'done':
            self.check_challenge_reward(cr, uid, ids, force=True, context=context)

        elif vals.get('state') == 'draft':
            # resetting progress
            if self.pool.get('gamification.goal').search(cr, uid, [('challenge_id', 'in', ids), ('state', 'in', ['inprogress', 'inprogress_update'])], context=context):
                raise osv.except_osv("Error", "You can not reset a challenge with unfinished goals.")
        
        write_res = super(gamification_challenge, self).write(cr, uid, ids, vals, context=context)

        # subscribe new users to the challenge
        if vals.get('user_ids'):
            # done with browse after super if changes in groups
            for challenge in self.browse(cr, uid, ids, context=context):
                self.message_subscribe_users(cr, uid, [challenge.id], [user.id for user in challenge.user_ids], context=context)

        return write_res


    ##### Update #####

    def _cron_update(self, cr, uid, context=None, ids=False):
        """Daily cron check.

        - Start planned challenges (in draft and with start_date = today)
        - Create the missing goals (eg: modified the challenge to add lines)
        - Update every running challenge
        """
        # start planned challenges
        planned_challenge_ids = self.search(cr, uid, [
            ('state', '=', 'draft'),
            ('start_date', '<=', fields.date.today())])
        if planned_challenge_ids:
            self.write(cr, uid, planned_challenge_ids, {'state': 'inprogress'}, context=context)

        # close planned challenges
        planned_challenge_ids = self.search(cr, uid, [
            ('state', '=', 'inprogress'),
            ('end_date', '>=', fields.date.today())])
        if planned_challenge_ids:
            self.write(cr, uid, planned_challenge_ids, {'state': 'done'}, context=context)

        if not ids:
            ids = self.search(cr, uid, [('state', '=', 'inprogress')], context=context)

        return self._update_all(cr, uid, ids, context=context)

    def _update_all(self, cr, uid, ids, context=None):
        """Update the challenges and related goals

        :param list(int) ids: the ids of the challenges to update, if False will
        update only challenges in progress."""
        if isinstance(ids, (int,long)):
            ids = [ids]

        goal_obj = self.pool.get('gamification.goal')

        # we use yesterday to update the goals that just ended
        yesterday = date.today() - timedelta(days=1)
        goal_ids = goal_obj.search(cr, uid, [
            ('challenge_id', 'in', ids),
            '|',
                ('state', 'in', ('inprogress', 'inprogress_update')),
                '&',
                    ('state', 'in', ('reached', 'failed')),
                    '|',
                        ('end_date', '>=', yesterday.strftime(DF)),
                        ('end_date', '=', False)
        ], context=context)
        # update every running goal already generated linked to selected challenges
        goal_obj.update(cr, uid, goal_ids, context=context)

        for challenge in self.browse(cr, uid, ids, context=context):
            if challenge.autojoin_group_id:
                # check in case of new users in challenge, this happens if manager removed users in challenge manually
                self.write(cr, uid, [challenge.id], {'user_ids': [(4, user.id) for user in challenge.autojoin_group_id.users]}, context=context)
            self.generate_goals_from_challenge(cr, uid, [challenge.id], context=context)

            if challenge.last_report_date != fields.date.today():
                # goals closed but still opened at the last report date
                closed_goals_to_report = goal_obj.search(cr, uid, [
                    ('challenge_id', '=', challenge.id),
                    ('start_date', '>=', challenge.last_report_date),
                    ('end_date', '<=', challenge.last_report_date)
                ])

                if fields.date.today() >= challenge.next_report_date:
                    self.report_progress(cr, uid, challenge, context=context)

                elif len(closed_goals_to_report) > 0:
                    # some goals need a final report
                    self.report_progress(cr, uid, challenge, subset_goal_ids=closed_goals_to_report, context=context)

        self.check_challenge_reward(cr, uid, ids, context=context)
        return True

    def quick_update(self, cr, uid, challenge_id, context=None):
        """Update all the goals of a challenge, no generation of new goals"""
        goal_ids = self.pool.get('gamification.goal').search(cr, uid, [('challenge_id', '=', challenge_id)], context=context)
        self.pool.get('gamification.goal').update(cr, uid, goal_ids, context=context)
        return True


    def action_check(self, cr, uid, ids, context=None):
        """Check a challenge

        Create goals that haven't been created yet (eg: if added users)
        Recompute the current value for each goal related"""
        return self._update_all(cr, uid, ids=ids, context=context)

    def action_report_progress(self, cr, uid, ids, context=None):
        """Manual report of a goal, does not influence automatic report frequency"""
        if isinstance(ids, (int,long)):
            ids = [ids]
        for challenge in self.browse(cr, uid, ids, context):
            self.report_progress(cr, uid, challenge, context=context)
        return True


    ##### Automatic actions #####

    def generate_goals_from_challenge(self, cr, uid, ids, context=None):
        """Generate the goals for each line and user.

        If goals already exist for this line and user, the line is skipped. This
        can be called after each change in the list of users or lines.
        :param list(int) ids: the list of challenge concerned"""

        goal_obj = self.pool.get('gamification.goal')
        for challenge in self.browse(cr, uid, ids, context):
            (start_date, end_date) = start_end_date_for_period(challenge.period)

            # if no periodicity, use challenge dates
            if not start_date and challenge.start_date:
                start_date = challenge.start_date
            if not end_date and challenge.end_date:
                end_date = challenge.end_date

            for line in challenge.line_ids:
                # FIXME: allow to restrict to a subset of users
                for user in challenge.user_ids:

                    domain = [('line_id', '=', line.id), ('user_id', '=', user.id)]
                    if start_date:
                        domain.append(('start_date', '=', start_date))

                    # goal already existing for this line ?
                    if len(goal_obj.search(cr, uid, domain, context=context)) > 0:

                        # resume canceled goals
                        domain.append(('state', '=', 'canceled'))
                        canceled_goal_ids = goal_obj.search(cr, uid, domain, context=context)
                        if canceled_goal_ids:
                            goal_obj.write(cr, uid, canceled_goal_ids, {'state': 'inprogress'}, context=context)
                            goal_obj.update(cr, uid, canceled_goal_ids, context=context)

                        # skip to next user
                        continue

                    values = {
                        'definition_id': line.definition_id.id,
                        'line_id': line.id,
                        'user_id': user.id,
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

                    new_goal_id = goal_obj.create(cr, uid, values, context)

                    goal_obj.update(cr, uid, [new_goal_id], context=context)

        return True

    ##### JS utilities #####

    def _get_serialized_challenge_lines(self, cr, uid, challenge, user_id=False, restrict_goal_ids=False, restrict_top=False, context=None):
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
                    'state': <gamification.goal state {draft,inprogress,inprogress_update,reached,failed,canceled}>,
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
            'state': <gamification.goal state {draft,inprogress,inprogress_update,reached,failed,canceled}>,                                
            'completeness': <percentage>,
            'current': <current value>,
        }
        """
        goal_obj = self.pool.get('gamification.goal')
        (start_date, end_date) = start_end_date_for_period(challenge.period)

        res_lines = []
        all_reached = True
        for line in challenge.line_ids:
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

            if challenge.visibility_mode == 'personal':
                if not user_id:
                    raise osv.except_osv(_('Error!'),_("Retrieving progress for personal challenge without user information"))
                domain.append(('user_id', '=', user_id))
                sorting = goal_obj._order
                limit = 1
            else:
                line_data.update({
                    'own_goal_id': False,
                    'goals': [],
                })
                sorting = "completeness desc, current desc"
                limit = False

            goal_ids = goal_obj.search(cr, uid, domain, order=sorting, limit=limit, context=context)
            ranking = 0
            for goal in goal_obj.browse(cr, uid, goal_ids, context=context):
                if challenge.visibility_mode == 'personal':
                    # limit=1 so only one result
                    line_data.update({
                        'id': goal.id,
                        'current': goal.current,
                        'completeness': goal.completeness,
                        'state': goal.state,
                    })
                    if goal.state != 'reached':
                        all_reached = False
                else:
                    ranking += 1
                    if user_id and goal.user_id.id == user_id:
                        line_data['own_goal_id'] = goal.id
                    elif restrict_top and ranking > restrict_top:
                        # not own goal, over top, skipping
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
            if goal_ids:
                res_lines.append(line_data)
        if all_reached:
            return []
        return res_lines

    ##### Reporting #####

    def report_progress(self, cr, uid, challenge, context=None, users=False, subset_goal_ids=False):
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
        if context is None:
            context = {}

        temp_obj = self.pool.get('email.template')
        ctx = context.copy()
        if challenge.visibility_mode == 'ranking':
            lines_boards = self._get_serialized_challenge_lines(cr, uid, challenge, user_id=False, restrict_goal_ids=subset_goal_ids, restrict_top=False, context=context)

            ctx.update({'challenge_lines': lines_boards})
            body_html = temp_obj.render_template(cr, uid, challenge.report_template_id.body_html, 'gamification.challenge', challenge.id, context=ctx)

            # send to every follower of the challenge
            self.message_post(cr, uid, challenge.id,
                body=body_html,
                context=context,
                subtype='mail.mt_comment')
            if challenge.report_message_group_id:
                self.pool.get('mail.group').message_post(cr, uid, challenge.report_message_group_id.id,
                    body=body_html,
                    context=context,
                    subtype='mail.mt_comment')

        else:
            # generate individual reports
            for user in users or challenge.user_ids:
                goals = self._get_serialized_challenge_lines(cr, uid, challenge, user.id, restrict_goal_ids=subset_goal_ids, context=context)
                if not goals:
                    continue

                ctx.update({'challenge_lines': goals})
                body_html = temp_obj.render_template(cr, user.id,  challenge.report_template_id.body_html, 'gamification.challenge', challenge.id, context=ctx)

                # send message only to users, not on the challenge
                self.message_post(cr, uid, 0,
                                  body=body_html,
                                  partner_ids=[(4, user.partner_id.id)],
                                  context=context,
                                  subtype='mail.mt_comment')
                if challenge.report_message_group_id:
                    self.pool.get('mail.group').message_post(cr, uid, challenge.report_message_group_id.id,
                                                             body=body_html,
                                                             context=context,
                                                             subtype='mail.mt_comment')
        return self.write(cr, uid, challenge.id, {'last_report_date': fields.date.today()}, context=context)

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
        return self.generate_goals_from_challenge(cr, SUPERUSER_ID, challenge_ids, context=context)

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

    def check_challenge_reward(self, cr, uid, ids, force=False, context=None):
        """Actions for the end of a challenge

        If a reward was selected, grant it to the correct users.
        Rewards granted at:
            - the end date for a challenge with no periodicity
            - the end of a period for challenge with periodicity
            - when a challenge is manually closed
        (if no end date, a running challenge is never rewarded)
        """
        if isinstance(ids, (int,long)):
            ids = [ids]
        context = context or {}
        for challenge in self.browse(cr, uid, ids, context=context):
            (start_date, end_date) = start_end_date_for_period(challenge.period, challenge.start_date, challenge.end_date)
            yesterday = date.today() - timedelta(days=1)
            if end_date == yesterday.strftime(DF) or force:
                # open chatter message
                message_body = _("The challenge %s is finished." % challenge.name)

                # reward for everybody succeeding
                rewarded_users = []
                if challenge.reward_id:
                    for user in challenge.user_ids:
                        reached_goal_ids = self.pool.get('gamification.goal').search(cr, uid, [
                            ('challenge_id', '=', challenge.id),
                            ('user_id', '=', user.id),
                            ('start_date', '=', start_date),
                            ('end_date', '=', end_date),
                            ('state', '=', 'reached')
                        ], context=context)
                        if len(reached_goal_ids) == len(challenge.line_ids):
                            self.reward_user(cr, uid, user.id, challenge.reward_id.id, context)
                            rewarded_users.append(user)

                    if rewarded_users:
                        message_body += _("<br/>Reward (badge %s) for every succeeding user was sent to %s." % (challenge.reward_id.name, ", ".join([user.name for user in rewarded_users])))
                    else:
                        message_body += _("<br/>Nobody has succeeded to reach every goal, no badge is rewared for this challenge.")

                # reward bests
                if challenge.reward_first_id:
                    (first_user, second_user, third_user) = self.get_top3_users(cr, uid, challenge, context)
                    if first_user:
                        self.reward_user(cr, uid, first_user.id, challenge.reward_first_id.id, context)
                        message_body += _("<br/>Special rewards were sent to the top competing users. The ranking for this challenge is :")
                        message_body += "<br/> 1. %s - %s" % (first_user.name, challenge.reward_first_id.name)
                    else:
                        message_body += _("Nobody reached the required conditions to receive special badges.")

                    if second_user and challenge.reward_second_id:
                        self.reward_user(cr, uid, second_user.id, challenge.reward_second_id.id, context)
                        message_body += "<br/> 2. %s - %s" % (second_user.name, challenge.reward_second_id.name)
                    if third_user and challenge.reward_third_id:
                        self.reward_user(cr, uid, third_user.id, challenge.reward_second_id.id, context)
                        message_body += "<br/> 3. %s - %s" % (third_user.name, challenge.reward_third_id.name)

                self.message_post(cr, uid, challenge.id, body=message_body, context=context)
        return True

    def get_top3_users(self, cr, uid, challenge, context=None):
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
        goal_obj = self.pool.get('gamification.goal')
        (start_date, end_date) = start_end_date_for_period(challenge.period, challenge.start_date, challenge.end_date)
        challengers = []
        for user in challenge.user_ids:
            all_reached = True
            total_completness = 0
            # every goal of the user for the running period
            goal_ids = goal_obj.search(cr, uid, [
                ('challenge_id', '=', challenge.id),
                ('user_id', '=', user.id),
                ('start_date', '=', start_date),
                ('end_date', '=', end_date)
            ], context=context)
            for goal in goal_obj.browse(cr, uid, goal_ids, context=context):
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

        if len(sorted_challengers) == 0 or (not challenge.reward_failure and not sorted_challengers[0]['all_reached']):
            # nobody succeeded
            return (False, False, False)
        if len(sorted_challengers) == 1 or (not challenge.reward_failure and not sorted_challengers[1]['all_reached']):
            # only one user succeeded
            return (sorted_challengers[0]['user'], False, False)
        if len(sorted_challengers) == 2 or (not challenge.reward_failure and not sorted_challengers[2]['all_reached']):
            # only one user succeeded
            return (sorted_challengers[0]['user'], sorted_challengers[1]['user'], False)
        return (sorted_challengers[0]['user'], sorted_challengers[1]['user'], sorted_challengers[2]['user'])

    def reward_user(self, cr, uid, user_id, badge_id, context=None):
        """Create a badge user and send the badge to him

        :param user_id: the user to reward
        :param badge_id: the concerned badge
        """
        badge_user_obj = self.pool.get('gamification.badge.user')
        user_badge_id = badge_user_obj.create(cr, uid, {'user_id': user_id, 'badge_id': badge_id}, context=context)
        return badge_user_obj._send_badge(cr, uid, [user_badge_id], context=context)


class gamification_challenge_line(osv.Model):
    """Gamification challenge line

    Predifined goal for 'gamification_challenge'
    These are generic list of goals with only the target goal defined
    Should only be created for the gamification_challenge object
    """

    _name = 'gamification.challenge.line'
    _description = 'Gamification generic goal for challenge'
    _order = "sequence, id"

    def on_change_definition_id(self, cr, uid, ids, definition_id=False, context=None):
        goal_definition = self.pool.get('gamification.goal.definition')
        if not definition_id:
            return {'value': {'definition_id': False}}
        goal_definition = goal_definition.browse(cr, uid, definition_id, context=context)
        ret = {
            'value': {
                'condition': goal_definition.condition,
                'definition_full_suffix': goal_definition.full_suffix
            }
        }
        return ret

    _columns = {
        'name': fields.related('definition_id', 'name', string="Name"),
        'challenge_id': fields.many2one('gamification.challenge',
            string='Challenge',
            required=True,
            ondelete="cascade"),
        'definition_id': fields.many2one('gamification.goal.definition',
            string='Goal Definition',
            required=True,
            ondelete="cascade"),
        'target_goal': fields.float('Target Value to Reach',
            required=True),
        'sequence': fields.integer('Sequence',
            help='Sequence number for ordering'),
        'condition': fields.related('definition_id', 'condition', type="selection",
            readonly=True, string="Condition", selection=[('lower', '<='), ('higher', '>=')]),
        'definition_suffix': fields.related('definition_id', 'suffix', type="char", readonly=True, string="Unit"),
        'definition_monetary': fields.related('definition_id', 'monetary', type="boolean", readonly=True, string="Monetary"),
        'definition_full_suffix': fields.related('definition_id', 'full_suffix', type="char", readonly=True, string="Suffix"),
    }

    _default = {
        'sequence': 1,
    }
