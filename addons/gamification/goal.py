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

    An individual goal for a user on a specified time period
    """

    _name = 'gamification.goal'
    _description = 'Gamification goal instance'
    _inherit = 'mail.thread'

    def _get_completeness(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for goal in self.browse(cr, uid, ids, context):
            res[goal.id] = compute_goal_completeness(goal.current, goal.target_goal)
        return res

    _columns = {
        'type_id' : fields.many2one('gamification.goal.type', 
            string='Goal Type',
            required=True,
            ondelete="cascade"),
        'user_id' : fields.many2one('res.users', string='User', required=True),
        'planline_id' : fields.many2one('gamification.goal.planline',
            string='Goal Plan',
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
        'last_update' : fields.date('Last Update',
            help="In case of manual goal, reminders are sent if the goal as not been updated for a while (defined in goal plan). Ignored in case of non-manual goal or goal not linked to a plan."), #
    }

    _defaults = {
        'current': 0,
        'state': 'inprogress',
        'start_date': fields.date.today,
    }

    def update(self, cr, uid, ids, context=None):
        """Update the goals to recomputes values and change of states"""

        for goal in self.browse(cr, uid, ids, context=context or {}):
            if goal.state not in ('inprogress','inprogress_update'): # reached ?
                continue

            if goal.type_id.computation_mode == 'sum':
                obj = self.pool.get(goal.type_id.model_id.model)
                field_name = goal.type_id.field_id.name
                field_date_name = goal.type_id.field_date_id.name
                
                domain = safe_eval(goal.type_id.domain)
                domain.append(('user_id', '=', goal.user_id.id))
                if goal.start_date:
                    domain.append((field_date_name, '>=', goal.start_date))
                if goal.end_date:
                    domain.append((field_date_name, '<=', goal.end_date))

                res = obj.read_group(cr, uid, domain, [field_name],
                    [''], context=context)
                print("domain", domain, "res", res)
                current = res[0][field_name]
                
            elif goal.type_id.computation_mode == 'count':
                obj = self.pool.get(goal.type_id.model_id.model)
                field_date_name = goal.type_id.field_date_id.name
                
                domain = safe_eval(goal.type_id.domain)
                domain.append(('user_id', '=', goal.user_id.id))
                if goal.start_date:
                    domain.append((field_date_name, '>=', goal.start_date))
                if goal.end_date:
                    domain.append((field_date_name, '<=', goal.end_date))

                res = obj.search(cr, uid, domain, context=context)
                print("domain", domain, "res", len(res), res)
                current = len(res)
            
            # else computation_mode == 'manually', nothing to compute

            towrite = {'current': current}
            if (goal.type_id.condition == 'plus' and current >= goal.target_goal) \
            or (goal.type_id.condition == 'minus' and current <= goal.target_goal):
                towrite['state'] = 'reached'

            elif goal.end_date and fields.date.today > goal.end_date:
                towrite['state'] = 'failed'

            self.write(cr, uid, [goal.id], towrite, context=context)
        return True

    def action_reach(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'reached'}, context=context)

    def action_fail(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'failed'}, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)

    def action_refresh(self, cr, uid, ids, context=None):
        return self.update(cr, uid, ids, context=context)


class gamification_goal_plan(osv.Model):
    """Ga;ification goal plan

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
        'remind_update_delays' : fields.integer('Remind delays',
            help="The number of days after which the user assigned to a manual goal will be reminded. Never reminded if no value is specified.")
        }

    _defaults = {
        'period': 'once',
        'state': 'draft',
        'visibility_mode' : 'progressbar',
        'report_message_frequency' : 'onchange',
    }

    def _check_nonzero_planline(self, cr, uid, ids, context=None):
        "checks that there is at least one planline set"
        for plan in self.browse(cr, uid, ids, context):
            if len(plan.planline_ids) < 1:
                return False
        return True

    def _check_nonzero_users(self, cr, uid, ids, context=None):
        "checks that there is at least one user set"
        for plan in self.browse(cr, uid, ids, context):
            if len(plan.user_ids) < 1 and plan.state != 'draft':
                return False
        return True

    _constraints = [
        (_check_nonzero_planline, "At least one planline is required to create a goal plan", ['planline_ids']),
        (_check_nonzero_users, "At least one user is required to create a non-draft goal plan", ['user_ids']),
    ]

    def action_start(self, cr, uid, ids, context=None):
        """Start a draft goal plan

        Change the state of the plan to in progress
        TODO: generate related goals"""
        return self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)

    def action_close(self, cr, uid, ids, context=None):
        """Close a plan in progress

        Change the state of the plan to in done
        TODO: close the related goals"""
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        """Cancel a plan in progress

        Change the state of the plan to draft
        TODO: close the related goals ?"""
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def action_reset(self, cr, uid, ids, context=None):
        """Reset a closed goal plan

        Change the state of the plan to in progress
        TODO: reopen unfinished goals ?"""
        return self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)


    def generate_goals_from_plan(self, cr, uid, ids, context=None):
        """Generate the lsit of goals fron a plan"""
        for plan in self.browse(cr, uid, ids, context):
            for planline in plan.planline_ids:
                for user in plan.user_ids:
                    goal_obj = self.pool.get('gamification.goal')
                    current = compute_current_value(planline.type_id, user_id)
                    goal_id = goal_obj.create(cr, uid, {
                        'type_id': planline.type_id,
                        'user_id': user.id,
                        'start_date':0,
                        'end_date':0,
                        'target_goal':planline.target_goal,
                        'state':'inprogress',
                        'last_update':fields.date.today,
                    }, context=context)


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
