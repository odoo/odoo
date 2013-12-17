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
from openerp.tools.safe_eval import safe_eval
from openerp.tools.translate import _

from datetime import date, datetime, timedelta

import logging

_logger = logging.getLogger(__name__)


class gamification_goal_definition(osv.Model):
    """Goal definition

    A goal definition contains the way to evaluate an objective
    Each module wanting to be able to set goals to the users needs to create
    a new gamification_goal_definition
    """
    _name = 'gamification.goal.definition'
    _description = 'Gamification goal definition'

    def _get_suffix(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, '')
        for goal in self.browse(cr, uid, ids, context=context):
            if goal.suffix and not goal.monetary:
                res[goal.id] = goal.suffix
            elif goal.monetary:
                # use the current user's company currency
                user = self.pool.get('res.users').browse(cr, uid, uid, context)
                if goal.suffix:
                    res[goal.id] = "%s %s" % (user.company_id.currency_id.symbol, goal.suffix)
                else:
                    res[goal.id] = user.company_id.currency_id.symbol
            else:
                res[goal.id] = ""
        return res

    _columns = {
        'name': fields.char('Goal Definition', required=True, translate=True),
        'description': fields.text('Goal Description'),
        'monetary': fields.boolean('Monetary Value', help="The target and current value are defined in the company currency."),
        'suffix': fields.char('Suffix', help="The unit of the target and current values", translate=True),
        'full_suffix': fields.function(_get_suffix, type="char", string="Full Suffix", help="The currency and suffix field"),
        'computation_mode': fields.selection([
                ('manually', 'Recorded manually'),
                ('count', 'Automatic: number of records'),
                ('sum', 'Automatic: sum on a field'),
                ('python', 'Automatic: execute a specific Python code'),
            ],
            string="Computation Mode",
            help="Defined how will be computed the goals. The result of the operation will be stored in the field 'Current'.",
            required=True),
        'display_mode': fields.selection([
                ('progress', 'Progressive (using numerical values)'),
                ('checkbox', 'Checkbox (done or not-done)'),
            ],
            string="Displayed as", required=True),
        'model_id': fields.many2one('ir.model',
            string='Model',
            help='The model object for the field to evaluate'),
        'field_id': fields.many2one('ir.model.fields',
            string='Field to Sum',
            help='The field containing the value to evaluate'),
        'field_date_id': fields.many2one('ir.model.fields',
            string='Date Field',
            help='The date to use for the time period evaluated'),
        'domain': fields.char("Filter Domain",
            help="Technical filters rules to apply. Use 'user.id' (without marks) to limit the search to the evaluated user.",
            required=True),
        'compute_code': fields.char('Compute Code',
            help="The name of the python method that will be executed to compute the current value. See the file gamification/goal_definition_data.py for examples."),
        'condition': fields.selection([
                ('higher', 'The higher the better'),
                ('lower', 'The lower the better')
            ],
            string='Goal Performance',
            help='A goal is considered as completed when the current value is compared to the value to reach',
            required=True),
        'action_id': fields.many2one('ir.actions.act_window', string="Action",
            help="The action that will be called to update the goal value."),
        'res_id_field': fields.char("ID Field of user",
            help="The field name on the user profile (res.users) containing the value for res_id for action.")
    }

    _defaults = {
        'condition': 'higher',
        'computation_mode': 'manually',
        'domain': "[]",
        'monetary': False,
        'display_mode': 'progress',
    }


class gamification_goal(osv.Model):
    """Goal instance for a user

    An individual goal for a user on a specified time period"""

    _name = 'gamification.goal'
    _description = 'Gamification goal instance'
    _inherit = 'mail.thread'

    def _get_completeness(self, cr, uid, ids, field_name, arg, context=None):
        """Return the percentage of completeness of the goal, between 0 and 100"""
        res = dict.fromkeys(ids, 0.0)
        for goal in self.browse(cr, uid, ids, context=context):
            if goal.definition_condition == 'higher':
                if goal.current >= goal.target_goal:
                    res[goal.id] = 100.0
                else:
                    res[goal.id] = round(100.0 * goal.current / goal.target_goal, 2)
            elif goal.current < goal.target_goal:
                # a goal 'lower than' has only two values possible: 0 or 100%
                res[goal.id] = 100.0
            else:
                res[goal.id] = 0.0
        return res

    def on_change_definition_id(self, cr, uid, ids, definition_id=False, context=None):
        goal_definition = self.pool.get('gamification.goal.definition')
        if not definition_id:
            return {'value': {'definition_id': False}}
        goal_definition = goal_definition.browse(cr, uid, definition_id, context=context)
        return {'value': {'computation_mode': goal_definition.computation_mode, 'definition_condition': goal_definition.condition}}

    _columns = {
        'definition_id': fields.many2one('gamification.goal.definition', string='Goal Definition', required=True, ondelete="cascade"),
        'user_id': fields.many2one('res.users', string='User', required=True),
        'line_id': fields.many2one('gamification.challenge.line', string='Goal Line', ondelete="cascade"),
        'challenge_id': fields.related('line_id', 'challenge_id',
            string="Challenge",
            type='many2one',
            relation='gamification.challenge',
            store=True),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),  # no start and end = always active
        'target_goal': fields.float('To Reach',
            required=True,
            track_visibility='always'),  # no goal = global index
        'current': fields.float('Current Value', required=True, track_visibility='always'),
        'completeness': fields.function(_get_completeness, type='float', string='Completeness'),
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
            track_visibility='always'),

        'computation_mode': fields.related('definition_id', 'computation_mode', type='char', string="Computation mode"),
        'remind_update_delay': fields.integer('Remind delay',
            help="The number of days after which the user assigned to a manual goal will be reminded. Never reminded if no value is specified."),
        'last_update': fields.date('Last Update',
            help="In case of manual goal, reminders are sent if the goal as not been updated for a while (defined in challenge). Ignored in case of non-manual goal or goal not linked to a challenge."),

        'definition_description': fields.related('definition_id', 'description', type='char', string='Definition Description', readonly=True),
        'definition_condition': fields.related('definition_id', 'condition', type='char', string='Definition Condition', readonly=True),
        'definition_suffix': fields.related('definition_id', 'full_suffix', type="char", string="Suffix", readonly=True),
        'definition_display': fields.related('definition_id', 'display_mode', type="char", string="Display Mode", readonly=True),
    }

    _defaults = {
        'current': 0,
        'state': 'draft',
        'start_date': fields.date.today,
    }
    _order = 'create_date desc, end_date desc, definition_id, id'

    def _check_remind_delay(self, cr, uid, goal, context=None):
        """Verify if a goal has not been updated for some time and send a
        reminder message of needed.

        :return: data to write on the goal object
        """
        if goal.remind_update_delay and goal.last_update:
            delta_max = timedelta(days=goal.remind_update_delay)
            last_update = datetime.strptime(goal.last_update, DF).date()
            if date.today() - last_update > delta_max and goal.state == 'inprogress':
                # generate a remind report
                temp_obj = self.pool.get('email.template')
                template_id = self.pool['ir.model.data'].get_object(cr, uid, 'gamification', 'email_template_goal_reminder', context)
                body_html = temp_obj.render_template(cr, uid, template_id.body_html, 'gamification.goal', goal.id, context=context)

                self.message_post(cr, uid, goal.id, body=body_html, partner_ids=[goal.user_id.partner_id.id], context=context, subtype='mail.mt_comment')
                return {'state': 'inprogress_update'}
        return {}

    def update(self, cr, uid, ids, context=None):
        """Update the goals to recomputes values and change of states

        If a manual goal is not updated for enough time, the user will be
        reminded to do so (done only once, in 'inprogress' state).
        If a goal reaches the target value, the status is set to reached
        If the end date is passed (at least +1 day, time not considered) without
        the target value being reached, the goal is set as failed."""

        for goal in self.browse(cr, uid, ids, context=context):
            towrite = {}
            if goal.state in ('draft', 'canceled'):
                # skip if goal draft or canceled
                continue

            if goal.definition_id.computation_mode == 'manually':
                towrite.update(self._check_remind_delay(cr, uid, goal, context))

            elif goal.definition_id.computation_mode == 'python':
                # execute the chosen method
                values = {'cr': cr, 'uid': goal.user_id.id, 'context': context, 'self': self.pool.get('gamification.goal.definition')}
                result = safe_eval(goal.definition_id.compute_code, values, {})

                if type(result) in (float, int, long) and result != goal.current:
                    towrite['current'] = result
                else:
                    _logger.exception(_('Unvalid return content from the evaluation of %s' % str(goal.definition_id.compute_code)))
                    # raise osv.except_osv(_('Error!'), _('Unvalid return content from the evaluation of %s' % str(goal.definition_id.compute_code)))

            else:  # count or sum
                obj = self.pool.get(goal.definition_id.model_id.model)
                field_date_name = goal.definition_id.field_date_id.name

                # eval the domain with user replaced by goal user object
                domain = safe_eval(goal.definition_id.domain, {'user': goal.user_id})

                #add temporal clause(s) to the domain if fields are filled on the goal
                if goal.start_date and field_date_name:
                    domain.append((field_date_name, '>=', goal.start_date))
                if goal.end_date and field_date_name:
                    domain.append((field_date_name, '<=', goal.end_date))

                if goal.definition_id.computation_mode == 'sum':
                    field_name = goal.definition_id.field_id.name
                    res = obj.read_group(cr, uid, domain, [field_name], [''], context=context)
                    new_value = res and res[0][field_name] or 0.0

                else:  # computation mode = count
                    new_value = obj.search(cr, uid, domain, context=context, count=True)

                #avoid useless write if the new value is the same as the old one
                if new_value != goal.current:
                    towrite['current'] = new_value

            # check goal target reached
            if (goal.definition_id.condition == 'higher' and towrite.get('current', goal.current) >= goal.target_goal) or (goal.definition_id.condition == 'lower' and towrite.get('current', goal.current) <= goal.target_goal):
                towrite['state'] = 'reached'

            # check goal failure
            elif goal.end_date and fields.date.today() > goal.end_date:
                towrite['state'] = 'failed'
            if towrite:
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
        """Overwrite the create method to add a 'no_remind_goal' field to True"""
        context = context or {}
        context['no_remind_goal'] = True
        return super(gamification_goal, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        """Overwrite the write method to update the last_update field to today

        If the current value is changed and the report frequency is set to On
        change, a report is generated
        """
        vals['last_update'] = fields.date.today()
        result = super(gamification_goal, self).write(cr, uid, ids, vals, context=context)
        for goal in self.browse(cr, uid, ids, context=context):
            if goal.state != "draft" and ('definition_id' in vals or 'user_id' in vals):
                # avoid drag&drop in kanban view
                raise osv.except_osv(_('Error!'), _('Can not modify the configuration of a started goal'))

            if vals.get('current'):
                if 'no_remind_goal' in context:
                    # new goals should not be reported
                    continue

                if goal.challenge_id and goal.challenge_id.report_message_frequency == 'onchange':
                    self.pool.get('gamification.challenge').report_progress(cr, SUPERUSER_ID, goal.challenge_id, users=[goal.user_id], context=context)
        return result

    def get_action(self, cr, uid, goal_id, context=None):
        """Get the ir.action related to update the goal

        In case of a manual goal, should return a wizard to update the value
        :return: action description in a dictionnary
        """
        goal = self.browse(cr, uid, goal_id, context=context)

        if goal.definition_id.action_id:
            #open a the action linked on the goal
            action = goal.definition_id.action_id.read()[0]

            if goal.definition_id.res_id_field:
                current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
                action['res_id'] = safe_eval(goal.definition_id.res_id_field, {'user': current_user})

                # if one element to display, should see it in form mode if possible
                views = action['views']
                for (view_id, mode) in action['views']:
                    if mode == "form":
                        views = [(view_id, mode)]
                        break
                action['views'] = views
            return action

        if goal.computation_mode == 'manually':
            #open a wizard window to update the value manually
            action = {
                'name': _("Update %s") % goal.definition_id.name,
                'id': goal_id,
                'type': 'ir.actions.act_window',
                'views': [[False, 'form']],
                'target': 'new',
            }
            action['context'] = {'default_goal_id': goal_id, 'default_current': goal.current}
            action['res_model'] = 'gamification.goal.wizard'
            return action

        return False


class goal_manual_wizard(osv.TransientModel):
    """Wizard to update a manual goal"""
    _name = 'gamification.goal.wizard'
    _columns = {
        'goal_id': fields.many2one("gamification.goal", string='Goal', required=True),
        'current': fields.float('Current'),
    }

    def action_update_current(self, cr, uid, ids, context=None):
        """Wizard action for updating the current value"""

        goal_obj = self.pool.get('gamification.goal')

        for wiz in self.browse(cr, uid, ids, context=context):
            towrite = {
                'current': wiz.current,
                'goal_id': wiz.goal_id.id,
            }
            goal_obj.write(cr, uid, [wiz.goal_id.id], towrite, context=context)
            goal_obj.update(cr, uid, [wiz.goal_id.id], context=context)
        return {}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
