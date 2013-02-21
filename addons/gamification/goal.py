# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2013 Tiny SPRL (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.safe_eval import safe_eval

from datetime import date, timedelta
import calendar

class gamification_goal_type(osv.Model):
    """Goal type definition

    A goal type defining a way to set an objective and evaluate it
    Each module wanting to be able to set goals to the users needs to create
    a new gamification_goal_type
    """
    _name = 'gamification.goal.type'
    _description = 'Gamification goal type'
    _order = "sequence"

    _columns = {
        'name': fields.char('Type Name', required=True),
        'description': fields.text('Description'),
        'computation_mode': fields.selection([
                ('sum','Sum'),
                ('count','Count'),
                ('manually','Manually')
            ],
            string="Mode of Computation",
            help="""How is computed the goal value :\n
- 'Sum' for the total of the values if the 'Evaluated field'\n
- 'Count' for the number of entries\n
- 'Manually' for user defined values""",
            required=True),
        'model_id': fields.many2one('ir.model',
            string='Model',
            help='The model object for the field to evaluate' ),
        'field_id': fields.many2one('ir.model.fields',
            string='Evaluated Field',
            help='The field containing the value to evaluate' ),
        'field_date_id': fields.many2one('ir.model.fields',
            string='Evaluated Date Field',
            help='The date to use for the time period evaluated'),
        'domain': fields.char("Domain",
            help="Technical filters rules to apply",
            required=True), # how to apply it ?
        'condition' : fields.selection([
                ('minus','<='),
                ('plus','>=')
            ],
            string='Validation Condition',
            help='A goal is considered as completed when the current value is compared to the value to reach',
            required=True),
        'sequence' : fields.integer('Sequence',
            help='Sequence number for ordering',
            required=True),
    }
    
    _order = 'sequence'
    _defaults = {
        'sequence': 1,
        'condition': 'plus',
        'computation_mode':'manually',
        'domain':"[]",
    }



def compute_goal_completeness(current, target_goal):
    # more than 100% case is handled by the widget
    if target_goal > 0:
        return 100.0 * current / target_goal
    else:
        return 0.0

class gamification_goal(osv.Model):
    """Goal instance for a user

    An individual goal for a user on a specified time period"""

    _name = 'gamification.goal'
    _description = 'Gamification goal instance'
    _inherit = 'mail.thread'

    def _get_completeness(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for goal in self.browse(cr, uid, ids, context):
            res[goal.id] = compute_goal_completeness(goal.current, goal.target_goal)
        return res

    def on_change_type_id(self, cr, uid, ids, type_id=False, context=None):
        goal_type = self.pool.get('gamification.goal.type')
        if not type_id:
            return {'value':{'type_id': False}}
        goal_type = goal_type.browse(cr, uid, type_id, context=context)
        ret = {'value' : {'computation_mode' : goal_type.computation_mode}}
        print(ret)
        return ret

    _columns = {
        'type_id' : fields.many2one('gamification.goal.type', 
            string='Goal Type',
            required=True,
            ondelete="cascade"),
        'user_id' : fields.many2one('res.users', string='User', required=True),
        'planline_id' : fields.many2one('gamification.goal.planline',
            string='Goal Planline',
            ondelete="cascade"),
        'start_date' : fields.date('Start Date'),
        'end_date' : fields.date('End Date'), # no start and end = always active
        'target_goal' : fields.float('To Reach',
            required=True,
            track_visibility = 'always'), # no goal = global index
        'current' : fields.float('Current',
            required=True,
            track_visibility = 'always'),
        'completeness': fields.function(_get_completeness,
            type='float',
            string='Completeness'),
        'state': fields.selection([
                ('inprogress', 'In progress'),
                ('inprogress_update', 'In progress (to update)'),
                ('reached', 'Reached'),
                ('failed', 'Failed'),
                ('canceled', 'Canceled'),
            ],
            string='State',
            required=True,
            track_visibility = 'always'),

        'computation_mode': fields.related('type_id','computation_mode',
            type='char', 
            string="Type computation mode"),
        'remind_update_delay' : fields.integer('Remind delay',
            help="The number of days after which the user assigned to a manual goal will be reminded. Never reminded if no value is specified."),
        'last_update' : fields.date('Last Update',
            help="In case of manual goal, reminders are sent if the goal as not been updated for a while (defined in goal plan). Ignored in case of non-manual goal or goal not linked to a plan."), #
    }

    _defaults = {
        'current': 0,
        'state': 'inprogress',
        'start_date': fields.date.today,
        'last_update': fields.date.today,
    }



    def _update_all(self, cr, uid, ids=False, context=None):
        """Update every goal in progress"""
        if not ids:
            ids = self.search(cr, uid, [('state', 'in', ('inprogress','inprogress_update'))])
        print("_update_all", ids)
        return self.update(cr, uid, ids, context=context)

    def update(self, cr, uid, ids, context=None, force_update=False):
        """Update the goals to recomputes values and change of states

        If a goal reaches the target value, the status is set to reach
        If the end date is passed (at least +1 day, time not considered) without
        the target value being reached, the goal is set as failed
        :param force_update: if false, only goals in progress are checked."""

        for goal in self.browse(cr, uid, ids, context=context or {}):
            if not force_update and goal.state not in ('inprogress','inprogress_update'): # reached ?
                continue

            if goal.type_id.computation_mode == 'manually':
                towrite = {'current': current}
                # check for remind to update
                if goal.remind_update_delay and goal.last_update:
                    delta_max = timedelta(days=goal.remind_update_delay)
                    if fields.date.today() - goal.last_update > delta_max:
                        towrite['state'] = 'inprogress_update'

            else: # count or sum
                obj = self.pool.get(goal.type_id.model_id.model)
                field_date_name = goal.type_id.field_date_id.name
                
                domain = safe_eval(goal.type_id.domain)
                domain.append(('user_id', '=', goal.user_id.id))
                if goal.start_date:
                    domain.append((field_date_name, '>=', goal.start_date))
                if goal.end_date:
                    domain.append((field_date_name, '<=', goal.end_date))

                if goal.type_id.computation_mode == 'sum':
                    field_name = goal.type_id.field_id.name
                    res = obj.read_group(cr, uid, domain, [field_name],
                        [''], context=context)
                    towrite = {'current': res[0][field_name]}
                
                else: # computation mode = count
                    res = obj.search(cr, uid, domain, context=context)
                    towrite = {'current': len(res)}

            # check goal target reached
            if (goal.type_id.condition == 'plus' \
                and towrite['current'] >= goal.target_goal) \
            or (goal.type_id.condition == 'minus' \
                and towrite['current'] <= goal.target_goal):
                towrite['state'] = 'reached'

            # check goal failure
            elif goal.end_date and fields.date.today() > goal.end_date:
                towrite['state'] = 'failed'
            
            self.write(cr, uid, [goal.id], towrite, context=context)
        return True

    def create_goal_from_plan(self, cr, uid, ids, planline_id, user_id, start_date, context=None):
        """If a goal for that planline and user is not already present, create it

        :param planline_id: id of the planline linked to the goal
        :param user_id: id of the user linked to the goal
        :param start_date: first day of the plan, False for non-automatic plans
            (where period is set to 'once')
        If a goal matching these three parameters is already present, no goal is
        created. In the case of manual plan (no start_date), the goal is always
        created.
        """

        obj = self.pool.get('gamification.goal')
        if start_date:
            domain = [('planline_id', '=', planline_id),
                ('user_id', '=', user_id),
                ('start_date', '=', start_date.isoformat())]
            goal_ids = obj.search(cr, uid, domain, context=context)
            if len(goal_ids) > 0:
                # already exist, skip
                return True

        planline = self.pool.get('gamification.goal.planline').browse(cr, uid, planline_id, context)
        values = {
            'type_id':planline.type_id.id,
            'planline_id':planline_id,
            'user_id':user_id,
            'target_goal':planline.target_goal,
        }

        if start_date:
            values['start_date'] = start_date.isoformat()
        if planline.plan_id.period != 'once':
            if planline.plan_id.period == 'daily':
                values['end_date'] = start_date + timedelta(days=1)
            elif planline.plan_id.period == 'weekly':
                values['end_date'] = start_date + timedelta(days=7)
            elif planline.plan_id.period == 'monthly':
                month_range = calendar.monthrange(start_date.year, start_date.month)
                values['end_date'] = start_date.replace(day=month_range[1])
            elif planline.plan_id.period == 'yearly':
                values['end_date'] = start_date.replace(month=12, day=31)
        if planline.plan_id.remind_update_delay:
            values['remind_update_delay'] = planline.plan_id.remind_update_delay
        
        new_goal_id = obj.create(cr, uid, values, context)
        self.update(cr, uid, [new_goal_id], context=context, force_update=True)


    def cancel_goals_from_plan(self, cr, uid, ids, planline_id, context=None):
        """Apply action to goals after it's plan has been canceled

        The status of every goal related to the planline is set to 'canceled
        :param planline_id: the id of the planline whose plan has been canceled'"""

        obj = self.pool.get('gamification.goal')
        goal_ids = obj.search(cr, uid, [('planline_id', '=', planline_id)], context=context)
        return self.write(cr, uid, goal_ids, {'state': 'canceled'}, context=context)

    def action_reach(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'reached'}, context=context)

    def action_fail(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'failed'}, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)

    def action_refresh(self, cr, uid, ids, context=None):
        """Update the state of goal, force to recomputes values"""
        return self.update(cr, uid, ids, context=context, force_update=True)


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
            string='Group',
            help='Group of users whose members will automatically be added to the users'),
        'period' : fields.selection([
                ('once', 'Manual'),
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
            string='Report to',
            help='Group that will receive the report in addition to the user'),
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

    def _update_all(self, cr, uid, ids=False, context=None):
        """Update every plan in progress"""
        if not ids:
            ids = self.search(cr, uid, [('state', '=', 'inprogress')])
        print("_update_all", ids)
        return self.generate_goals_from_plan(cr, uid, ids, context=context)

    def action_start(self, cr, uid, ids, context=None):
        """Start a draft goal plan

        Change the state of the plan to in progress"""
        self.generate_goals_from_plan(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)

    def action_check(self, cr, uid, ids, context=None):
        """Check a goal plan in progress

        Create goals that haven't been created yet (eg: if added users of planlines)
        Recompute the current value for each goal related"""
        self.generate_goals_from_plan(cr, uid, ids, context=context)
        for plan in self.browse(cr, uid, ids, context):
            if plan.state != 'improgress':
                continue

            for planline in plan.planline_ids:
                goal_obj = self.pool.get('gamification.goal')
                goal_ids = goal_obj.search(cr, uid, [('planline_id', '=', planline.id)] , context=context)
                goal_obj.update(cr, uid, goal_ids, context=context, force_update=True)

        return True


    def action_close(self, cr, uid, ids, context=None):
        """Close a plan in progress

        Change the state of the plan to in done
        Does NOT close the related goals, this is handled by the goal itself"""
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def action_reset(self, cr, uid, ids, context=None):
        """Reset a closed goal plan

        Change the state of the plan to in progress
        Closing a pan does not affect the goals so reset as well"""
        return self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        """Cancel a plan in progress

        Change the state of the plan to draft
        Cancel the related goals"""
        self.write(cr, uid, ids, {'state': 'draft'}, context=context)
        for plan in self.browse(cr, uid, ids, context):
            for planline in plan.planline_ids:
                goal_obj = self.pool.get('gamification.goal')
                goal_obj.cancel_goals_from_plan(cr, uid, ids, planline.id, context=context)

        return True

    def generate_goals_from_plan(self, cr, uid, ids, context=None):
        """Generate the lsit of goals fron a plan"""
        for plan in self.browse(cr, uid, ids, context):
            today = date.today() #fields.date.today()
            if plan.period == 'daily':
                start_date = today
            elif plan.period == 'weekly':
                delta = timedelta(days=today.weekday())
                start_date = today - delta
            elif plan.period == 'monthly':
                delta = timedelta(days=today.day-1)
                start_date = today - delta
            elif plan.period == 'yearly':
                start_date = today.replace(month=1, day=1)
            elif plan.period == 'once':
                start_date = False # for manual goal, start each time

            for planline in plan.planline_ids:
                for user in plan.user_ids:
                    goal_obj = self.pool.get('gamification.goal')
                    goal_obj.create_goal_from_plan(cr, uid, ids, planline.id, user.id, start_date, context=context)

        return True

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
