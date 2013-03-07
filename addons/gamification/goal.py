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
from openerp.tools.safe_eval import safe_eval

from templates import TemplateHelper

from datetime import date, datetime, timedelta

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
        'name': fields.char('Type Name', required=True, translate=True),
        'description': fields.text('Description'),
        'unit': fields.char('Unit', help="The unit of the target and current values", translate=True),
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
                ('lower','<='),
                ('higher','>=')
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
        'condition': 'higher',
        'computation_mode':'manually',
        'domain':"[]",
    }



class gamification_goal(osv.Model):
    """Goal instance for a user

    An individual goal for a user on a specified time period"""

    _name = 'gamification.goal'
    _description = 'Gamification goal instance'
    _inherit = 'mail.thread'

    def _get_completeness(self, cr, uid, ids, field_name, arg, context=None):
        """Return the percentage of completeness of the goal, between 0 and 100"""
        res = {}
        for goal in self.browse(cr, uid, ids, context):
            if goal.current > 0:
                res[goal.id] = min(100, round(100.0 * goal.current / goal.target_goal, 2))
            else:
                res[goal.id] = 0.0
            
        return res

    def on_change_type_id(self, cr, uid, ids, type_id=False, context=None):
        goal_type = self.pool.get('gamification.goal.type')
        if not type_id:
            return {'value':{'type_id': False}}
        goal_type = goal_type.browse(cr, uid, type_id, context=context)
        ret = {'value' : {'computation_mode' : goal_type.computation_mode}}
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
                ('draft', 'Draft'),
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
            help="In case of manual goal, reminders are sent if the goal as not been updated for a while (defined in goal plan). Ignored in case of non-manual goal or goal not linked to a plan."),
        'type_description': fields.related('type_id','description',
            type='char',
            string='Type Description'),
        'type_unit': fields.related('type_id','unit',
            type='char',
            string='Type Description'),
    }

    _defaults = {
        'current': 0,
        'state': 'draft',
        'start_date': fields.date.today,
    }


    def update(self, cr, uid, ids, context=None):
        """Update the goals to recomputes values and change of states

        If a manual goal is not updated for enough time, the user will be
        reminded to do so (done only once, in 'inprogress' state).
        If a goal reaches the target value, the status is set to reached
        If the end date is passed (at least +1 day, time not considered) without
        the target value being reached, the goal is set as failed."""
        
        for goal in self.browse(cr, uid, ids, context=context or {}):
            if goal.state in ('draft','canceled'):
                # skip if goal draft or canceled
                continue
            if goal.last_update and goal.end_date and goal.last_update > goal.end_date:
                # skip if a goal is finished (updated after the goal end date)
                continue

            if goal.type_id.computation_mode == 'manually':
                towrite = {'current':goal.current}
                # check for remind to update
                if goal.remind_update_delay and goal.last_update:
                    delta_max = timedelta(days=goal.remind_update_delay)
                    last_update = datetime.strptime(goal.last_update,'%Y-%m-%d').date()
                    if date.today() - last_update > delta_max and goal.state == 'inprogress':
                        towrite['state'] = 'inprogress_update'

                        # generate a remind report
                        template_env = TemplateHelper()
                        body_html = template_env.get_template('reminder.mako').render({'object':goal})
                        self.message_post(cr, uid, goal.id,
                            body=body_html,
                            partner_ids=[goal.user_id.partner_id.id],
                            context=context,
                            subtype='mail.mt_comment')
                        
            else: # count or sum
                obj = self.pool.get(goal.type_id.model_id.model)
                field_date_name = goal.type_id.field_date_id.name
                
                domain = safe_eval(goal.type_id.domain, 
                    {'user_id': goal.user_id.id})
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
            if (goal.type_id.condition == 'higher' \
                and towrite['current'] >= goal.target_goal) \
            or (goal.type_id.condition == 'lower' \
                and towrite['current'] <= goal.target_goal):
                towrite['state'] = 'reached'

            # check goal failure
            elif goal.end_date and fields.date.today() > goal.end_date:
                towrite['state'] = 'failed'
            
            self.write(cr, uid, [goal.id], towrite, context=context)
        return True

    def action_start(self, cr, uid, ids, context=None):
        """Mark a goal as started.

        This should only be used when creating goals manually (in draft state)"""
        self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)
        return self.update(cr, uid, ids, context=context)

    def action_reach(self, cr, uid, ids, context=None):
        """Mark a goal as reached.

        If the target goal condition is not met, the state will be reset to In
        Progress at the next goal update until the end date."""
        return self.write(cr, uid, ids, {'state': 'reached'}, context=context)

    def action_fail(self, cr, uid, ids, context=None):
        """Set the state of the goal to failed.

        A failed goal will be ignored in future checks."""
        return self.write(cr, uid, ids, {'state': 'failed'}, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        """Reset the completion after setting a goal as reached or failed.

        This is only the current state, if the date and/or target criterias
        match the conditions for a change of state, this will be applied at the 
        next goal update."""
        return self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)

    def create(self, cr, uid, vals, context=None):
        """Overwrite the create method to add a 'just_created' field to True"""
        context = context or {}
        context['just_created'] = True
        return super(gamification_goal, self).create(cr, uid, vals, context=context)
        
    def write(self, cr, uid, ids, vals, context=None):
        """Overwrite the write method to update the last_update field to today

        If the current value is changed and the report frequency is set to On 
        change, q report is generated"""
        for goal in self.browse(cr, uid, ids, vals):
            vals['last_update'] = fields.date.today()

            if 'current' in vals:
                if 'just_created' in context:
                    # new goals should not be reported
                    continue

                if goal.planline_id and goal.planline_id.plan_id.report_message_frequency == 'onchange':
                    plan_obj = self.pool.get('gamification.goal.plan')
                    plan_obj.report_progress(cr, uid, goal.planline_id.plan_id, users=[goal.user_id], context=context)
        return super(gamification_goal, self).write(cr, uid, ids, vals, context=context)
        
