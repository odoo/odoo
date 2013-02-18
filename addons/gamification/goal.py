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

from datetime import date

GAMIFICATION_GOAL_STATE = [
    ('inprogress','In progress'),
    ('reached','Reached'),
    ('failed','Failed'),
]

GAMIFICATION_PLAN_STATE = [
    ('draft','Draft'),
    ('inprogress','In progress'),
    ('done','Done'),
]

GAMIFICATION_PERIOD_STATE = [
    ('once','Manual'),
    ('daily','Daily'),
    ('weekly','Weekly'),
    ('monthly','Monthly'),
    ('yearly', 'Yearly')
]

GAMIFICATION_COMPUTATION_MODE = [
    ('sum','Sum'),
    ('count','Count'),
    ('manually','Manually')
]

GAMIFICATION_VALIDATION_CONDITION = [
    ('minus','<='),
    ('plus','>=')
]

GAMIFICATION_REPORT_MODE = [
    ('board','Leader board'),
    ('progressbar','Personal progressbar')
]

GAMIFICATION_REPORT_FREQ = [
    ('never','Never'),
    ('onchange','On change'),
    ('daily','Daily'),
    ('weekly','Weekly'),
    ('monthly','Monthly'),
    ('yearly', 'Yearly')
]


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
        'computation_mode': fields.selection(GAMIFICATION_COMPUTATION_MODE,
            string="Mode of Computation",
            help="""How is computed the goal value :\n
- 'Sum' for the total of the values if the 'Evaluated field'\n
- 'Count' for the number of entries\n
- 'Manually' for user defined values""",
            required=True),
        'model_id': fields.many2one('ir.model',
            string='Modeel',
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
        'condition' : fields.selection(GAMIFICATION_VALIDATION_CONDITION,
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
            # more than 100% case is handled by the widget
            if goal.target_goal > 0:
                res[goal.id] = 100.0 * goal.current / goal.target_goal
            else:
                res[goal.id] = 0.0
        return res

    _columns = {
        'type_id' : fields.many2one('gamification.goal.type', 
            string='Goal Type',
            required=True),
        'user_id' : fields.many2one('res.users', string='User', required=True),
        'plan_id' : fields.many2one('gamification.goal.plan',
            string='Goal Plan'),
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
            string='Occupation'),
        'state': fields.selection(GAMIFICATION_GOAL_STATE,
            string='State',
            required=True,
            track_visibility = 'always'),
    }

    _defaults = {
        'current': 0,
        'state': 'inprogress',
        'start_date': fields.date.today,
    }

    def action_reach(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'reached'}, context=context)

    def action_fail(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'failed'}, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)



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
        'period' : fields.selection(GAMIFICATION_PERIOD_STATE,
            string='Period',
            help='Period of automatic goal assigment, will be done manually if none is selected',
            required=True),
        'state': fields.selection(GAMIFICATION_PLAN_STATE,
            string='State',
            required=True),
        'report_mode':fields.selection(GAMIFICATION_REPORT_MODE,
            string="Mode",
            help='How is displayed the results, shared or in a signle progressbar',
            required=True),
        'report_message_frequency':fields.selection(GAMIFICATION_REPORT_FREQ,
            string="Frequency",
            required=True),
        'report_message_group_id' : fields.many2one('mail.group',
            string='Report to',
            help='Group that will receive the report in addition to the user'),
        'report_header' : fields.text('Report Header'),
        }

    _defaults = {
        'period': 'once',
        'state': 'draft',
        'report_mode' : 'progressbar',
        'report_message_frequency' : 'onchange',
    }

    def action_start(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)

    def action_close(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)



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
            string='Plan'),
        'type_id' : fields.many2one('gamification.goal.type',
            string='Goal Type',
            required=True),
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
