# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
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

from templates import TemplateHelper

from datetime import date, datetime, timedelta
import calendar


def start_end_date_for_period(period):
    """Return the start and end date for a goal period based on today

    :return (start_date, end_date), datetime.date objects, False if the period is
    not defined or unknown"""
    today = date.today()
    if period == 'daily':
        start_date = today
        end_date = start_date # ? + timedelta(days=1)
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
    else: # period == 'once':
        start_date = False # for manual goal, start each time
        end_date = False
    
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

    _columns = {
        'name' : fields.char('Plan Name', required=True),
        'user_ids' : fields.many2many('res.users',
            string='Users',
            help="list of users to which the goal will be set"),
        'planline_ids' : fields.one2many('gamification.goal.planline',
            'plan_id',
            string='Planline',
            help="list of goals that will be set",
            required=True),
        'autojoin_group_id' : fields.many2one('res.groups',
            string='Auto-join Group',
            help='Group of users whose members will automatically be added to the users'),
        'period' : fields.selection([
                ('once', 'No Periodicity'),
                ('daily', 'Daily'),
                ('weekly', 'Weekly'),
                ('monthly', 'Monthly'),
                ('yearly', 'Yearly')
            ],
            string='Periodicity',
            help='Period of automatic goal assigment, will be done manually if none is selected',
            required=True),
        'state': fields.selection([
                ('draft', 'Draft'),
                ('inprogress', 'In progress'),
                ('done', 'Done'),
            ],
            string='State',
            required=True),
        'visibility_mode':fields.selection([
                ('board','Leader board'),
                ('progressbar','Personal progressbar')
            ],
            string="Visibility",
            help='How are displayed the results, shared or in a single progressbar',
            required=True),
        'report_message_frequency':fields.selection([
                ('never','Never'),
                ('onchange','On change'),
                ('daily','Daily'),
                ('weekly','Weekly'),
                ('monthly','Monthly'),
                ('yearly', 'Yearly')
            ],
            string="Frequency",
            required=True),
        'report_message_group_id' : fields.many2one('mail.group',
            string='Send a copy to',
            help='Group that will receive a copy of the report in addition to the user'),
        'report_header' : fields.text('Report Header'),
        'remind_update_delay' : fields.integer('Remind delay',
            help="The number of days after which the user assigned to a manual goal will be reminded. Never reminded if no value is specified.")
        }

    _defaults = {
        'period': 'once',
        'state': 'draft',
        'visibility_mode' : 'progressbar',
        'report_message_frequency' : 'onchange',
    }

    def _check_nonzero_planline(self, cr, uid, ids, context=None):
        """checks that there is at least one planline set"""
        for plan in self.browse(cr, uid, ids, context):
            if len(plan.planline_ids) < 1:
                return False
        return True

    def _check_nonzero_users(self, cr, uid, ids, context=None):
        """checks that there is at least one user set"""
        for plan in self.browse(cr, uid, ids, context):
            if len(plan.user_ids) < 1 and plan.state != 'draft':
                return False
        return True

    _constraints = [
        (_check_nonzero_planline, "At least one planline is required to create a goal plan", ['planline_ids']),
        (_check_nonzero_users, "At least one user is required to create a non-draft goal plan", ['user_ids']),
    ]

    def write(self, cr, uid, ids, vals, context=None):
        """Overwrite the write method to add the user of groups"""
        write_res = super(gamification_goal_plan, self).write(cr, uid, ids, vals, context=context)
        
        # add users when change the group auto-subscription
        if 'autojoin_group_id' in vals:
            new_group = self.pool.get('res.groups').browse(cr, uid, vals['autojoin_group_id'], context=context)
            self.plan_subscribe_users(cr, uid, ids, [user.id for user in new_group.users], context=context)
        return write_res

    def _update_all(self, cr, uid, context=None, ids=False):
        """Update the plans

        Create the goals for planlines not linked to goals (eg: modified the 
            plan to add planlines)
        :param list(int) ids: the ids of the plans to update, if False will 
        update only goals in progress."""

        if not ids:
            ids = self.search(cr, uid, [('state', '=', 'inprogress')])

        goal_obj = self.pool.get('gamification.goal')
        planline_obj = self.pool.get('gamification.goal.planline')

        self.generate_goals_from_plan(cr, uid, ids, context=context)
        for plan in self.browse(cr, uid, ids, context):
            for planline in plan.planline_ids:
                goal_ids = goal_obj.search(cr, uid, [('planline_id', '=', planline.id)] , context=context)
                goal_obj.update(cr, uid, goal_ids, context=context)

    def action_start(self, cr, uid, ids, context=None):
        """Start a draft goal plan

        Change the state of the plan to in progress"""
        self.generate_goals_from_plan(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)

    def action_check(self, cr, uid, ids, context=None):
        """Check a goal plan

        Create goals that haven't been created yet (eg: if added users of planlines)
        Recompute the current value for each goal related"""
        return self._update_all(cr, uid, ids, context=context)    


    def action_close(self, cr, uid, ids, context=None):
        """Close a plan in progress

        Change the state of the plan to in done
        Does NOT close the related goals, this is handled by the goal itself"""
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
        for plan in self.browse(cr, uid, ids, context):
            for planline in plan.planline_ids:
                goal_obj = self.pool.get('gamification.goal')

                goal_ids = goal_obj.search(cr, uid, [('planline_id', '=', planline.id)], context=context)
                goal_obj.write(cr, uid, goal_ids, {'state': 'canceled'}, context=context)

        return True

    def action_show_related_goals(self, cr, uid, ids, context=None):
        """ This opens goal view with a restriction to the list of goals from this plan only
            @return: the goal view
        """
        # get ids of related goals 
        goal_obj = self.pool.get('gamification.goal')
        related_goal_ids = []
        for plan in self.browse(cr, uid, ids, context=context):
            for planline in plan.planline_ids:
                goal_ids = goal_obj.search(cr, uid, [('planline_id', '=', planline.id)], context=context)
                related_goal_ids.extend(goal_ids)
        
        # process the new view
        if context is None:
            context = {}
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid ,'gamification','goals_from_plan_act', context=context)
        res['context'] = context
        res['context'].update({
            'default_id': related_goal_ids
        })
        res['domain'] = [('id','in', related_goal_ids)]
        return res

    def generate_goals_from_plan(self, cr, uid, ids, context=None):
        """Generate the list of goals linked to a plan.

        If goals already exist for this planline, the planline is skipped. This 
        can be called after each change in the user or planline list.
        :param list(int) ids: the list of plan concerned"""

        for plan in self.browse(cr, uid, ids, context):
            (start_date, end_date) = start_end_date_for_period(plan.period)

            for planline in plan.planline_ids:
                for user in plan.user_ids:
                    #self.create_goal_from_plan(cr, uid, ids, planline.id, user.id, start_date, context=context)

                    goal_obj = self.pool.get('gamification.goal')
                    domain = [('planline_id', '=', planline.id),
                            ('user_id', '=', user.id)]
                    if start_date:
                        domain.append(('start_date', '=', start_date))
                    
                    # goal existing for this planline ?
                    if len(goal_obj.search(cr, uid, domain, context=context)) > 0:

                        # resume canceled goals
                        domain.append(('state', '=', 'canceled'))
                        canceled_goal_ids = goal_obj.search(cr, uid, domain, context=context)
                        goal_obj.write(cr, uid, canceled_goal_ids, {'state': 'inprogress'}, context=context)
                        goal_obj.update(cr, uid, canceled_goal_ids, context=context)
                        
                        # skip to next user
                        continue

                    values = {
                        'type_id':planline.type_id.id,
                        'planline_id':planline.id,
                        'user_id':user.id,
                        'target_goal':planline.target_goal,
                        'state':'inprogress',
                    }
            
                    if start_date:
                        values['start_date'] = start_date.isoformat()
                    if end_date:
                        values['end_date'] = end_date.isoformat()

                    if planline.plan_id.remind_update_delay:
                        values['remind_update_delay'] = planline.plan_id.remind_update_delay

                    new_goal_id = goal_obj.create(cr, uid, values, context)
                    
                    goal_obj.update(cr, uid, [new_goal_id], context=context)

        return True


    def plan_subscribe_users(self, cr, uid, ids, new_user_ids, context=None):
        """ Add the following users to plans

        :param ids: ids of plans to which the users will be added
        :param new_user_ids: ids of the users to add"""

        for plan in self.browse(cr,uid, ids, context):
            subscription = [user.id for user in plan.user_ids]
            subscription.extend(new_user_ids)
            # remove duplicates
            unified_subscription = list(set(subscription))
            self.write(cr, uid, ids, {'user_ids': [(4, uid) for uid in unified_subscription]}, context=context)
        return True


    def report_progress(self, cr, uid, ids, context=None, users=False):
        """Post report about the progress of the goals

        :param list(int) ids: the list of plan ids that need to be reported
        :param list(res.users) users: the list of users that are concerned by
          the report. If False, will send the report to every user concerned
          (goal users and group that recieves a copy). Only used for plan with
          a visibility mode set to 'personal'."""
        
        context = context or {}
        goal_obj = self.pool.get('gamification.goal')
        template_env = TemplateHelper()

        for plan in self.browse(cr, uid, ids, context=context):

            if plan.visibility_mode == 'board':
                # generate a shared report
                planlines_boards = []
                for planline in plan.planline_ids:

                    (start_date, end_date) = start_end_date_for_period(plan.period)
                    domain = [
                        ('planline_id', '=', planline.id),
                        ('state', 'in', ('inprogress', 'inprogress_update',
                            'reached', 'failed')),
                    ]
                    if start_date:
                        domain.append(('start_date', '=', start_date.isoformat()))
                    

                    board_goals = []
                    goal_ids = goal_obj.search(cr, uid, domain, context=context)
                    for goal in goal_obj.browse(cr, uid, goal_ids, context=context):
                        board_goals.append({
                            'user': goal.user_id,
                            'current':goal.current,
                            'target_goal':goal.target_goal,
                            'completeness':goal.completeness,
                        })

                    # most complete first, current if same percentage (eg: if several 100%)
                    sorted_board = enumerate(sorted(board_goals, key=lambda k: (k['completeness'], k['current']), reverse=True))
                    planlines_boards.append({'goal_type':planline.type_id.name, 'board_goals':sorted_board})

                body_html = template_env.get_template('group_progress.mako').render({'object':plan, 'planlines_boards':planlines_boards})
                self.message_post(cr, uid, plan.id,
                    body=body_html,
                    partner_ids=[(6, 0, [user.partner_id.id for user in plan.user_ids])],
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
                    goal_ids = self.get_current_related_goals(cr, uid, plan.id, user.id, context=context)
                    if len(goal_ids) == 0:
                        continue

                    variables = {
                        'object':plan,
                        'user':user,
                        'goals':goal_obj.browse(cr, uid, goal_ids, context=context)
                    }
                    body_html = template_env.get_template('personal_progress.mako').render(variables)
                    
                    # FIXME huge blank space
                    self.message_post(cr, uid, plan.id,
                        body=body_html,
                        partner_ids=[(6, 0, [user.partner_id.id])],
                        context=context,
                        subtype='mail.mt_comment')
                    if plan.report_message_group_id:
                        self.pool.get('mail.group').message_post(cr, uid, plan.report_message_group_id.id,
                            body=body_html,
                            context=context,
                            subtype='mail.mt_comment')
        return True


    def get_current_related_goals(self, cr, uid, plan_id, user_id, context=None):
        """Get the ids of goals linked to a plan for the current instance

        If several goals are linked to the same planline and user, only the
        latest instance of the plan is checked (eg: if the plan is monthly,
        return the goals started the 1st of this month).
        """

        plan = self.browse(cr, uid, plan_id, context=context)
        (start_date, end_date) = start_end_date_for_period(plan.period)

        goal_obj = self.pool.get('gamification.goal')
        related_goal_ids = []

        for planline in plan.planline_ids:
            domain = [('planline_id', '=', planline.id),
                ('user_id', '=', user_id),
                ('state','in',('inprogress','inprogress_update','reached'))]

            if start_date:
                domain.append(('start_date', '=', start_date.isoformat()))

            goal_ids = goal_obj.search(cr, uid, domain, context=context)
            related_goal_ids.extend(goal_ids)

        return related_goal_ids

class gamification_goal_planline(osv.Model):
    """Gamification goal planline

    Predifined goal for 'gamification_goal_plan'
    These are generic list of goals with only the target goal defined
    Should only be created for the gamification_goal_plan object
    """

    _name = 'gamification.goal.planline'
    _description = 'Gamification generic goal for plan'
    _order = "sequence_type"


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

    _columns = {
        'plan_id' : fields.many2one('gamification.goal.plan',
            string='Plan',
            ondelete="cascade"),
        'type_id' : fields.many2one('gamification.goal.type',
            string='Goal Type',
            required=True,
            ondelete="cascade"),
        'target_goal' : fields.float('Target Value to Reach',
            required=True),
        'sequence_type' : fields.related('type_id','sequence',
            type='integer',
            string='Sequence',
            readonly=True,
            store={
                'gamification.goal.type': (_get_planline_types, ['sequence'], 10),
                }),
    }