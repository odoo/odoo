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

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from openerp.tools.translate import _

# from templates import TemplateHelper

from datetime import date, datetime, timedelta
import calendar
import logging
_logger = logging.getLogger(__name__)


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
        return (start_date.strftime(DF), end_date.strftime(DF))
    else:
        return (start_date, end_date)


class gamification_goal_plan(osv.Model):
    """Gamification goal plan

    Set of predifined goals to be able to automate goal settings or
    quickly apply several goals manually to a group of users

    If 'user_ids' is defined and 'period' is different than 'one', the set will
    be assigned to the users for each period (eg: every 1st of each month if
    'monthly' is selected)
    """

    _name = 'gamification.goal.plan'
    _description = 'Gamification goal plan'
    _inherit = 'mail.thread'

    def _get_next_report_date(self, cr, uid, ids, field_name, arg, context=None):
        """Return the next report date based on the last report date and report
        period.

        :return: a string in DEFAULT_SERVER_DATE_FORMAT representing the date"""
        res = {}
        for plan in self.browse(cr, uid, ids, context):
            last = datetime.strptime(plan.last_report_date, DF).date()
            if plan.report_message_frequency == 'daily':
                next = last + timedelta(days=1)
                res[plan.id] = next.strftime(DF)
            elif plan.report_message_frequency == 'weekly':
                next = last + timedelta(days=7)
                res[plan.id] = next.strftime(DF)
            elif plan.report_message_frequency == 'monthly':
                month_range = calendar.monthrange(last.year, last.month)
                next = last.replace(day=month_range[1]) + timedelta(days=1)
                res[plan.id] = next.strftime(DF)
            elif plan.report_message_frequency == 'yearly':
                res[plan.id] = last.replace(year=last.year + 1).strftime(DF)
            # frequency == 'once', reported when closed only
            else:
                res[plan.id] = False

        return res

    def _planline_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, 0)
        for plan in self.browse(cr, uid, ids, context):
            res[plan.id] = len(plan.planline_ids)
        return res

    _columns = {
        'name': fields.char('Challenge Name', required=True, translate=True),
        'description': fields.text('Description', translate=True),
        'state': fields.selection([
                ('draft', 'Draft'),
                ('inprogress', 'In Progress'),
                ('done', 'Done'),
            ],
            string='State',
            required=True),
        'manager_id': fields.many2one('res.users',
            string='Responsible', help="The user responsible for the challenge."),

        'user_ids': fields.many2many('res.users', 'user_ids',
            string='Users',
            help="List of users to which the goal will be set"),
        'autojoin_group_id': fields.many2one('res.groups',
            string='Auto-subscription Group',
            help='Group of users whose members will automatically be added to the users'),

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

        'proposed_user_ids': fields.many2many('res.users', 'proposed_user_ids',
            string="Suggest to users"),

        'planline_ids': fields.one2many('gamification.goal.planline', 'plan_id',
            string='Planline',
            help="List of goals that will be set",
            required=True),
        'planline_count': fields.function(_planline_count, type='integer', string="Planlines"),

        'reward_id': fields.many2one('gamification.badge', string="For Every Succeding User"),
        'reward_first_id': fields.many2one('gamification.badge', string="For 1st user"),
        'reward_second_id': fields.many2one('gamification.badge', string="For 2nd user"),
        'reward_third_id': fields.many2one('gamification.badge', string="For 3rd user"),
        'reward_failure': fields.boolean('Reward Bests if not Succeeded?'),

        'visibility_mode': fields.selection([
                ('progressbar', 'Individual Goals'),
                ('board', 'Leader Board (Group Ranking)'),
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
        'report_header': fields.text('Report Header'),
        'remind_update_delay': fields.integer('Non-updated manual goals will be reminded after',
            help="Never reminded if no value or zero is specified."),
        'last_report_date': fields.date('Last Report Date'),
        'next_report_date': fields.function(_get_next_report_date,
            type='date',
            string='Next Report Date'),

        'category': fields.selection([
                ('hr', 'Human Ressources / Engagement'),
                ('other', 'Settings / Gamification Tools'),
            ],
            string="Appears in", help="Define the visibility of the challenge through menus", required=True),
        }

    _defaults = {
        'period': 'once',
        'state': 'draft',
        'visibility_mode': 'progressbar',
        'report_message_frequency': 'never',
        'last_report_date': fields.date.today,
        'start_date': fields.date.today,
        'manager_id': lambda s, cr, uid, c: uid,
        'category': 'hr',
        'reward_failure': False,
    }

    _sort = 'end_date, start_date, name'

    def write(self, cr, uid, ids, vals, context=None):
        """Overwrite the write method to add the user of groups"""
        context = context or {}
        if not ids:
            return True

        # unsubscribe removed users from the plan
        # users are not able to manually unsubscribe to challenges so should
        # do it for them when not concerned anymore
        if vals.get('user_ids'):
            for action_tuple in vals['user_ids']:
                if action_tuple[0] == 3:
                    # form (3, ID), remove one
                    self.message_unsubscribe_users(cr, uid, ids, [action_tuple[1]], context=context)
                if action_tuple[0] == 5:
                    # form (5,), remove all
                    for plan in self.browse(cr, uid, ids, context=context):
                        self.message_unsubscribe_users(cr, uid, [plan.id], [user.id for user in plan.user_ids], context=context)
                if action_tuple[0] == 6:
                    # form (6, False, [IDS]), replace by IDS
                    for plan in self.browse(cr, uid, ids, context=context):
                        removed_users = set([user.id for user in plan.user_ids]) - set(action_tuple[2])
                        self.message_unsubscribe_users(cr, uid, [plan.id], list(removed_users), context=context)

        write_res = super(gamification_goal_plan, self).write(cr, uid, ids, vals, context=context)

        # add users when change the group auto-subscription
        if 'autojoin_group_id' in vals:
            new_group = self.pool.get('res.groups').browse(cr, uid, vals['autojoin_group_id'], context=context)
            group_user_ids = [user.id for user in new_group.users]
            for plan in self.browse(cr, uid, ids, context=context):
                self.write(cr, uid, [plan.id], {'user_ids': [(4, user) for user in group_user_ids]}, context=context)

        # subscribe new users to the plan
        if 'user_ids' in vals:
            for plan in self.browse(cr, uid, ids, context=context):
                self.message_subscribe_users(cr, uid, ids, [user.id for user in plan.user_ids], context=context)
        return write_res

    ##### Update #####

    def _cron_update(self, cr, uid, context=None, ids=False):
        """Daily cron check.

        Start planned plans (in draft and with start_date = today)
        Create the goals for planlines not linked to goals (eg: modified the
            plan to add planlines)
        Update every plan running
        """
        if not context: context = {}

        # start planned plans
        planned_plan_ids = self.search(cr, uid, [
            ('state', '=', 'draft'),
            ('start_date', '<=', fields.date.today())])
        self.action_start(cr, uid, planned_plan_ids, context=context)

        # close planned plans
        planned_plan_ids = self.search(cr, uid, [
            ('state', '=', 'inprogress'),
            ('end_date', '>=', fields.date.today())])
        self.action_close(cr, uid, planned_plan_ids, context=context)

        if not ids:
            ids = self.search(cr, uid, [('state', '=', 'inprogress')], context=context)

        return self._update_all(cr, uid, ids, context=context)

    def _update_all(self, cr, uid, ids, context=None):
        """Update the plans and related goals

        :param list(int) ids: the ids of the plans to update, if False will
        update only plans in progress."""
        if not context: context = {}
        goal_obj = self.pool.get('gamification.goal')

        # we use yesterday to update the goals that just ended
        yesterday = date.today() - timedelta(days=1)
        goal_ids = goal_obj.search(cr, uid, [
            ('plan_id', 'in', ids),
            '|',
                ('state', 'in', ('inprogress', 'inprogress_update')),
                '&',
                    ('state', 'in', ('reached', 'failed')),
                    '|',
                        ('end_date', '>=', yesterday.strftime(DF)),
                        ('end_date', '=', False)
        ], context=context)
        # update every running goal already generated linked to selected plans
        goal_obj.update(cr, uid, goal_ids, context=context)

        for plan in self.browse(cr, uid, ids, context=context):
            if plan.autojoin_group_id:
                # check in case of new users in plan, this happens if manager removed users in plan manually
                self.write(cr, uid, [plan.id], {'user_ids': [(4, user.id) for user in plan.autojoin_group_id.users]}, context=context)
            self.generate_goals_from_plan(cr, uid, [plan.id], context=context)

            # goals closed but still opened at the last report date
            closed_goals_to_report = goal_obj.search(cr, uid, [
                ('plan_id', '=', plan.id),
                ('start_date', '>=', plan.last_report_date),
                ('end_date', '<=', plan.last_report_date)
            ])

            if len(closed_goals_to_report) > 0:
                # some goals need a final report
                self.report_progress(cr, uid, plan, subset_goal_ids=closed_goals_to_report, context=context)

            if fields.date.today() == plan.next_report_date:
                self.report_progress(cr, uid, plan, context=context)

        self.check_challenge_reward(cr, uid, ids, context=context)
        return True

    def quick_update(self, cr, uid, plan_id, context=None):
        """Update all the goals of a plan, no generation of new goals"""
        if not context: context = {}
        goal_ids = self.pool.get('gamification.goal').search(cr, uid, [('plan_id', '=', plan_id)], context=context)
        self.pool.get('gamification.goal').update(cr, uid, goal_ids, context=context)
        return True

    ##### User actions #####

    def action_start(self, cr, uid, ids, context=None):
        """Start a draft goal plan

        Change the state of the plan to in progress and generate related goals
        """
        # subscribe users if autojoin group
        for plan in self.browse(cr, uid, ids, context=context):
            if plan.autojoin_group_id:
                self.write(cr, uid, [plan.id], {'user_ids': [(4, user.id) for user in plan.autojoin_group_id.users]}, context=context)

            self.write(cr, uid, plan.id, {'state': 'inprogress'}, context=context)
            self.message_post(cr, uid, plan.id, body="New challenge started.", context=context)
        return self.generate_goals_from_plan(cr, uid, ids, context=context)

    def action_check(self, cr, uid, ids, context=None):
        """Check a goal plan

        Create goals that haven't been created yet (eg: if added users of planlines)
        Recompute the current value for each goal related"""
        return self._update_all(cr, uid, ids=ids, context=context)

    def action_close(self, cr, uid, ids, context=None):
        """Close a plan in progress

        Change the state of the plan to in done
        Does NOT close the related goals, this is handled by the goal itself"""
        self.check_challenge_reward(cr, uid, ids, force=True, context=context)
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def action_reset(self, cr, uid, ids, context=None):
        """Reset a closed goal plan

        Change the state of the plan to in progress
        Closing a plan does not affect the goals so neither does reset"""
        return self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        """Cancel a plan in progress

        Change the state of the plan to draft
        Cancel the related goals"""
        self.write(cr, uid, ids, {'state': 'draft'}, context=context)
        goal_ids = self.pool.get('gamification.goal').search(cr, uid, [('plan_id', 'in', ids)], context=context)
        self.pool.get('gamification.goal').write(cr, uid, goal_ids, {'state': 'canceled'}, context=context)

        return True

    def action_report_progress(self, cr, uid, ids, context=None):
        """Manual report of a goal, does not influence automatic report frequency"""
        for plan in self.browse(cr, uid, ids, context):
            self.report_progress(cr, uid, plan, context=context)
        return True

    ##### Automatic actions #####

    def generate_goals_from_plan(self, cr, uid, ids, context=None):
        """Generate the list of goals linked to a plan.

        If goals already exist for this planline, the planline is skipped. This
        can be called after each change in the user or planline list.
        :param list(int) ids: the list of plan concerned"""

        for plan in self.browse(cr, uid, ids, context):
            (start_date, end_date) = start_end_date_for_period(plan.period)

            # if no periodicity, use plan dates
            if not start_date and plan.start_date:
                start_date = plan.start_date
            if not end_date and plan.end_date:
                end_date = plan.end_date

            for planline in plan.planline_ids:
                for user in plan.user_ids:

                    goal_obj = self.pool.get('gamification.goal')
                    domain = [('planline_id', '=', planline.id), ('user_id', '=', user.id)]
                    if start_date:
                        domain.append(('start_date', '=', start_date))

                    # goal already existing for this planline ?
                    if len(goal_obj.search(cr, uid, domain, context=context)) > 0:

                        # resume canceled goals
                        domain.append(('state', '=', 'canceled'))
                        canceled_goal_ids = goal_obj.search(cr, uid, domain, context=context)
                        goal_obj.write(cr, uid, canceled_goal_ids, {'state': 'inprogress'}, context=context)
                        goal_obj.update(cr, uid, canceled_goal_ids, context=context)

                        # skip to next user
                        continue

                    values = {
                        'type_id': planline.type_id.id,
                        'planline_id': planline.id,
                        'user_id': user.id,
                        'target_goal': planline.target_goal,
                        'state': 'inprogress',
                    }

                    if start_date:
                        values['start_date'] = start_date
                    if end_date:
                        values['end_date'] = end_date

                    if planline.plan_id.remind_update_delay:
                        values['remind_update_delay'] = planline.plan_id.remind_update_delay

                    new_goal_id = goal_obj.create(cr, uid, values, context)

                    goal_obj.update(cr, uid, [new_goal_id], context=context)

        return True

    ##### JS utilities #####

    def get_board_goal_info(self, cr, uid, plan, subset_goal_ids=False, context=None):
        """Get the list of latest goals for a plan, sorted by user ranking for each planline"""

        goal_obj = self.pool.get('gamification.goal')
        planlines_boards = []
        (start_date, end_date) = start_end_date_for_period(plan.period)

        for planline in plan.planline_ids:

            domain = [
                ('planline_id', '=', planline.id),
                ('state', 'in', ('inprogress', 'inprogress_update',
                                 'reached', 'failed')),
            ]

            if subset_goal_ids:
                goal_ids = goal_obj.search(cr, uid, domain, context=context)
                common_goal_ids = [goal for goal in goal_ids if goal in subset_goal_ids]
            else:
                # if no subset goals, use the dates for restriction
                if start_date:
                    domain.append(('start_date', '=', start_date))
                if end_date:
                    domain.append(('end_date', '=', end_date))
                common_goal_ids = goal_obj.search(cr, uid, domain, context=context)

            board_goals = [goal for goal in goal_obj.browse(cr, uid, common_goal_ids, context=context)]

            if len(board_goals) == 0:
                # planline has no generated goals
                continue

            # most complete first, current if same percentage (eg: if several 100%)
            sorted_board = enumerate(sorted(board_goals, key=lambda k: (k.completeness, k.current), reverse=True))
            planlines_boards.append({'goal_type': planline.type_id, 'board_goals': sorted_board, 'target_goal': planline.target_goal})
        return planlines_boards

    def get_indivual_goal_info(self, cr, uid, user_id, plan, subset_goal_ids=False, context=None):
        """Get the list of latest goals of a user for a plan"""
        domain = [
            ('plan_id', '=', plan.id),
            ('user_id', '=', user_id),
            ('state', 'in', ('inprogress', 'inprogress_update',
                             'reached', 'failed')),
        ]
        goal_obj = self.pool.get('gamification.goal')
        (start_date, end_date) = start_end_date_for_period(plan.period)

        if subset_goal_ids:
            # use the domain for safety, don't want irrelevant report if wrong argument
            goal_ids = goal_obj.search(cr, uid, domain, context=context)
            related_goal_ids = [goal for goal in goal_ids if goal in subset_goal_ids]
        else:
            # if no subset goals, use the dates for restriction
            if start_date:
                domain.append(('start_date', '=', start_date))
            if end_date:
                domain.append(('end_date', '=', end_date))
            related_goal_ids = goal_obj.search(cr, uid, domain, context=context)

        if len(related_goal_ids) == 0:
            return False

        goals = []
        all_done = True
        for goal in goal_obj.browse(cr, uid, related_goal_ids, context=context):
            if goal.end_date:
                if goal.end_date < fields.date.today():
                    # do not include goals of previous plan run
                    continue
                else:
                    all_done = False
            else:
                if goal.state == 'inprogress' or goal.state == 'inprogress_update':
                    all_done = False

            goals.append(goal)

        if all_done:
            # skip plans where all goal are done or failed
            return False
        else:
            return goals

    ##### Reporting #####

    def report_progress(self, cr, uid, plan, context=None, users=False, subset_goal_ids=False):
        """Post report about the progress of the goals

        :param plan: the plan object that need to be reported
        :param users: the list(res.users) of users that are concerned by
          the report. If False, will send the report to every user concerned
          (goal users and group that receive a copy). Only used for plan with
          a visibility mode set to 'personal'.
        :param goal_ids: the list(int) of goal ids linked to the plan for
          the report. If not specified, use the goals for the current plan
          period. This parameter can be used to produce report for previous plan
          periods.
        :param subset_goal_ids: a list(int) of goal ids to restrict the report
        """

        context = context or {}
        # template_env = TemplateHelper()
        temp_obj = self.pool.get('email.template')
        ctx = context.copy()
        if plan.visibility_mode == 'board':
            planlines_boards = self.get_board_goal_info(cr, uid, plan, subset_goal_ids, context)

            ctx.update({'planlines_boards': planlines_boards})
            template_id = self.pool['ir.model.data'].get_object(cr, uid, 'gamification', 'email_template_goal_progress_group', context)
            body_html = temp_obj.render_template(cr, uid, template_id.body_html, 'gamification.goal.plan', plan.id, context=context)

            # body_html = template_env.get_template('group_progress.mako').render({'object': plan, 'planlines_boards': planlines_boards, 'uid': uid})

            # send to every follower of the plan
            self.message_post(cr, uid, plan.id,
                body=body_html,
                context=context,
                subtype='mail.mt_comment')
            if plan.report_message_group_id:
                self.pool.get('mail.group').message_post(cr, uid, plan.report_message_group_id.id,
                    body=body_html,
                    context=context,
                    subtype='mail.mt_comment')

        else:
            # generate individual reports
            for user in users or plan.user_ids:
                goals = self.get_indivual_goal_info(cr, uid, user.id, plan, subset_goal_ids, context=context)
                if not goals:
                    continue

                ctx.update({'goals': goals})
                template_id = self.pool['ir.model.data'].get_object(cr, uid, 'gamification', 'email_template_goal_progress_perso', context)
                body_html = temp_obj.render_template(cr, user.id, template_id.body_html, 'gamification.goal.plan', plan.id, context=context)
                # send message only to users
                self.message_post(cr, uid, 0,
                                  body=body_html,
                                  partner_ids=[(4, user.partner_id.id)],
                                  context=context,
                                  subtype='mail.mt_comment')
                if plan.report_message_group_id:
                    self.pool.get('mail.group').message_post(cr, uid, plan.report_message_group_id.id,
                                                             body=body_html,
                                                             context=context,
                                                             subtype='mail.mt_comment')
        return self.write(cr, uid, plan.id, {'last_report_date': fields.date.today()}, context=context)

    ##### Challenges #####

    def accept_challenge(self, cr, uid, plan_ids, context=None, user_id=None):
        """The user accept the suggested challenge"""
        context = context or {}
        user_id = user_id or uid
        user = self.pool.get('res.users').browse(cr, uid, user_id, context=context)
        message = "%s has joined the challenge" % user.name
        self.message_post(cr, uid, plan_ids, body=message, context=context)
        self.write(cr, uid, plan_ids, {'proposed_user_ids': [(3, user_id)], 'user_ids': [(4, user_id)]}, context=context)
        return self.generate_goals_from_plan(cr, uid, plan_ids, context=context)

    def discard_challenge(self, cr, uid, plan_ids, context=None, user_id=None):
        """The user discard the suggested challenge"""
        context = context or {}
        user_id = user_id or uid
        user = self.pool.get('res.users').browse(cr, uid, user_id, context=context)
        message = "%s has refused the challenge" % user.name
        self.message_post(cr, uid, plan_ids, body=message, context=context)
        return self.write(cr, uid, plan_ids, {'proposed_user_ids': (3, user_id)}, context=context)

    def reply_challenge_wizard(self, cr, uid, plan_id, context=None):
        context = context or {}
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'gamification', 'challenge_wizard')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['res_id'] = plan_id
        return result

    def check_challenge_reward(self, cr, uid, plan_ids, force=False, context=None):
        """Actions for the end of a challenge

        If a reward was selected, grant it to the correct users.
        Rewards granted at:
            - the end date for a challenge with no periodicity
            - the end of a period for challenge with periodicity
            - when a challenge is manually closed
        (if no end date, a running challenge is never rewarded)
        """
        context = context or {}
        for plan in self.browse(cr, uid, plan_ids, context=context):
            (start_date, end_date) = start_end_date_for_period(plan.period, plan.start_date, plan.end_date)
            yesterday = date.today() - timedelta(days=1)
            if end_date == yesterday.strftime(DF) or force:
                # open chatter message
                message_body = _("The challenge %s is finished." % plan.name)

                # reward for everybody succeeding
                rewarded_users = []
                if plan.reward_id:
                    for user in plan.user_ids:
                        reached_goal_ids = self.pool.get('gamification.goal').search(cr, uid, [
                            ('plan_id', '=', plan.id),
                            ('user_id', '=', user.id),
                            ('start_date', '=', start_date),
                            ('end_date', '=', end_date),
                            ('state', '=', 'reached')
                        ], context=context)
                        if len(reached_goal_ids) == len(plan.planline_ids):
                            self.reward_user(cr, uid, user.id, plan.reward_id.id, context)
                            rewarded_users.append(user)

                    if rewarded_users:
                        message_body += _("<br/>Reward (badge %s) for every succeeding user was sent to %s." % (plan.reward_id.name, ", ".join([user.name for user in rewarded_users])))
                    else:
                        message_body += _("<br/>Nobody has succeeded to reach every goal, no badge is rewared for this challenge.")

                # reward bests
                if plan.reward_first_id:
                    (first_user, second_user, third_user) = self.get_top3_users(cr, uid, plan, context)
                    if first_user:
                        self.reward_user(cr, uid, first_user.id, plan.reward_first_id.id, context)
                        message_body += _("<br/>Special rewards were sent to the top competing users. The ranking for this challenge is :")
                        message_body += "<br/> 1. %s - %s" % (first_user.name, plan.reward_first_id.name)
                    else:
                        message_body += _("Nobody reached the required conditions to receive special badges.")

                    if second_user and plan.reward_second_id:
                        self.reward_user(cr, uid, second_user.id, plan.reward_second_id.id, context)
                        message_body += "<br/> 2. %s - %s" % (second_user.name, plan.reward_second_id.name)
                    if third_user and plan.reward_third_id:
                        self.reward_user(cr, uid, third_user.id, plan.reward_second_id.id, context)
                        message_body += "<br/> 3. %s - %s" % (third_user.name, plan.reward_third_id.name)

                self.message_post(cr, uid, plan.id, body=message_body, context=context)
        return True

    def get_top3_users(self, cr, uid, plan, context=None):
        """Get the top 3 users for a defined plan

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
        (start_date, end_date) = start_end_date_for_period(plan.period, plan.start_date, plan.end_date)
        challengers = []
        for user in plan.user_ids:
            all_reached = True
            total_completness = 0
            # every goal of the user for the running period
            goal_ids = goal_obj.search(cr, uid, [
                ('plan_id', '=', plan.id),
                ('user_id', '=', user.id),
                ('start_date', '=', start_date),
                ('end_date', '=', end_date)
            ], context=context)
            for goal in goal_obj.browse(cr, uid, goal_ids, context=context):
                if goal.state != 'reached':
                    all_reached = False
                if goal.type_condition == 'higher':
                    # can be over 100
                    total_completness += 100.0 * goal.current / goal.target_goal
                elif goal.state == 'reached':
                    # for lower goals, can not get percentage so 0 or 100
                    total_completness += 100

            challengers.append({'user': user, 'all_reached': all_reached, 'total_completness': total_completness})
        sorted_challengers = sorted(challengers, key=lambda k: (k['all_reached'], k['total_completness']), reverse=True)

        if len(sorted_challengers) == 0 or (not plan.reward_failure and not sorted_challengers[0]['all_reached']):
            # nobody succeeded
            return (False, False, False)
        if len(sorted_challengers) == 1 or (not plan.reward_failure and not sorted_challengers[1]['all_reached']):
            # only one user succeeded
            return (sorted_challengers[0]['user'], False, False)
        if len(sorted_challengers) == 2 or (not plan.reward_failure and not sorted_challengers[2]['all_reached']):
            # only one user succeeded
            return (sorted_challengers[0]['user'], sorted_challengers[1]['user'], False)
        return (sorted_challengers[0]['user'], sorted_challengers[1]['user'], sorted_challengers[2]['user'])

    def reward_user(self, cr, uid, user_id, badge_id, context=None):
        """Create a badge user and send the badge to him"""
        user_badge_id = self.pool.get('gamification.badge.user').create(cr, uid, {'user_id': user_id, 'badge_id': badge_id}, context=context)
        return self.pool.get('gamification.badge').send_badge(cr, uid, badge_id, [user_badge_id], user_from=None, context=context)


class gamification_goal_planline(osv.Model):
    """Gamification goal planline

    Predifined goal for 'gamification_goal_plan'
    These are generic list of goals with only the target goal defined
    Should only be created for the gamification_goal_plan object
    """

    _name = 'gamification.goal.planline'
    _description = 'Gamification generic goal for plan'
    _order = "sequence, sequence_type, id"

    def _get_planline_types(self, cr, uid, ids, context=None):
        """Return the ids of planline items related to the gamification.goal.type
        objects in 'ids (used to update the value of 'sequence_type')'"""

        result = {}
        for goal_type in self.pool.get('gamification.goal.type').browse(cr, uid, ids, context=context):
            domain = [('type_id', '=', goal_type.id)]
            planline_ids = self.pool.get('gamification.goal.planline').search(cr, uid, domain, context=context)
            for p_id in planline_ids:
                result[p_id] = True
        return result.keys()

    def on_change_type_id(self, cr, uid, ids, type_id=False, context=None):
        goal_type = self.pool.get('gamification.goal.type')
        if not type_id:
            return {'value': {'type_id': False}}
        goal_type = goal_type.browse(cr, uid, type_id, context=context)
        ret = {'value': {
            'type_condition': goal_type.condition,
            'type_full_suffix': goal_type.full_suffix}}
        return ret

    _columns = {
        'name': fields.related('type_id', 'name', string="Name"),
        'plan_id': fields.many2one('gamification.goal.plan',
            string='Plan',
            required=True,
            ondelete="cascade"),
        'type_id': fields.many2one('gamification.goal.type',
            string='Goal Type',
            required=True,
            ondelete="cascade"),
        'target_goal': fields.float('Target Value to Reach',
            required=True),
        'sequence': fields.integer('Sequence',
            help='Sequence number for ordering'),
        'sequence_type': fields.related('type_id', 'sequence',
            type='integer',
            string='Sequence',
            readonly=True,
            store={
                'gamification.goal.type': (_get_planline_types, ['sequence'], 10),
                }),
        'type_condition': fields.related('type_id', 'condition', type="selection",
            readonly=True, string="Condition", selection=[('lower', '<='), ('higher', '>=')]),
        'type_suffix': fields.related('type_id', 'suffix', type="char", readonly=True, string="Unit"),
        'type_monetary': fields.related('type_id', 'monetary', type="boolean", readonly=True, string="Monetary"),
        'type_full_suffix': fields.related('type_id', 'full_suffix', type="char", readonly=True, string="Suffix"),
    }

    _default = {
        'sequence': 1,
    }
