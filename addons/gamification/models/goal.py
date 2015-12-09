# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv, expression
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from openerp.tools.safe_eval import safe_eval
from openerp.tools.translate import _
from openerp.exceptions import UserError

import logging
import time
from datetime import date, datetime, timedelta

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
                ('boolean', 'Exclusive (done or not-done)'),
            ],
            string="Displayed as", required=True),
        'model_id': fields.many2one('ir.model',
            string='Model',
            help='The model object for the field to evaluate'),
        # model_inherited_model_ids can be removed in master.
        # It was only used to force a domain in the form view which is now set by `on_change_model_id`
        'model_inherited_model_ids': fields.related('model_id', 'inherited_model_ids', type="many2many", obj="ir.model",
            string="Inherited models", readonly="True"),
        'field_id': fields.many2one('ir.model.fields',
            string='Field to Sum',
            help='The field containing the value to evaluate'),
        'field_date_id': fields.many2one('ir.model.fields',
            string='Date Field',
            help='The date to use for the time period evaluated'),
        'domain': fields.char("Filter Domain",
            help="Domain for filtering records. General rule, not user depending, e.g. [('state', '=', 'done')]. The expression can contain reference to 'user' which is a browse record of the current user if not in batch mode.",
            required=True),

        'batch_mode': fields.boolean('Batch Mode',
            help="Evaluate the expression in batch instead of once for each user"),
        'batch_distinctive_field': fields.many2one('ir.model.fields',
            string="Distinctive field for batch user",
            help="In batch mode, this indicates which field distinct one user form the other, e.g. user_id, partner_id..."),
        'batch_user_expression': fields.char("Evaluted expression for batch mode",
            help="The value to compare with the distinctive field. The expression can contain reference to 'user' which is a browse record of the current user, e.g. user.id, user.partner_id.id..."),
        'compute_code': fields.text('Python Code',
            help="Python code to be executed for each user. 'result' should contains the new current value. Evaluated user can be access through object.user_id."),
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
            help="The field name on the user profile (res.users) containing the value for res_id for action."),
    }

    _defaults = {
        'condition': 'higher',
        'computation_mode': 'manually',
        'domain': "[]",
        'monetary': False,
        'display_mode': 'progress',
    }

    def number_following(self, cr, uid, model_name="mail.thread", context=None):
        """Return the number of 'model_name' objects the user is following

        The model specified in 'model_name' must inherit from mail.thread
        """
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return self.pool.get('mail.followers').search(cr, uid, [('res_model', '=', model_name), ('partner_id', '=', user.partner_id.id)], count=True, context=context)

    def _check_domain_validity(self, cr, uid, ids, context=None):
        # take admin as should always be present
        superuser = self.pool['res.users'].browse(cr, uid, SUPERUSER_ID, context=context)
        for definition in self.browse(cr, uid, ids, context=context):
            if definition.computation_mode not in ('count', 'sum'):
                continue

            obj = self.pool[definition.model_id.model]
            try:
                domain = safe_eval(definition.domain, {'user': superuser})
                # demmy search to make sure the domain is valid
                obj.search(cr, uid, domain, context=context, count=True)
            except (ValueError, SyntaxError), e:
                msg = e.message or (e.msg + '\n' + e.text)
                raise UserError(_("The domain for the definition %s seems incorrect, please check it.\n\n%s" % (definition.name, msg)))
        return True

    def create(self, cr, uid, vals, context=None):
        res_id = super(gamification_goal_definition, self).create(cr, uid, vals, context=context)
        if vals.get('computation_mode') in ('count', 'sum'):
            self._check_domain_validity(cr, uid, [res_id], context=context)

        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        res = super(gamification_goal_definition, self).write(cr, uid, ids, vals, context=context)
        if vals.get('computation_mode', 'count') in ('count', 'sum') and (vals.get('domain') or vals.get('model_id')):
            self._check_domain_validity(cr, uid, ids, context=context)

        return res

    def on_change_model_id(self, cr, uid, ids, model_id, context=None):
        """Force domain for the `field_id` and `field_date_id` fields"""
        if not model_id:
            return {'domain': {'field_id': expression.FALSE_DOMAIN, 'field_date_id': expression.FALSE_DOMAIN}}
        model = self.pool['ir.model'].browse(cr, uid, model_id, context=context)
        model_fields_domain = ['|', ('model_id', '=', model_id), ('model_id', 'in', model.inherited_model_ids.ids)]
        model_date_fields_domain = expression.AND([[('ttype', 'in', ('date', 'datetime'))], model_fields_domain])
        return {'domain': {'field_id': model_fields_domain, 'field_date_id': model_date_fields_domain}}


class gamification_goal(osv.Model):
    """Goal instance for a user

    An individual goal for a user on a specified time period"""

    _name = 'gamification.goal'
    _description = 'Gamification goal instance'

    def _get_completion(self, cr, uid, ids, field_name, arg, context=None):
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
        'user_id': fields.many2one('res.users', string='User', required=True, auto_join=True, ondelete="cascade"),
        'line_id': fields.many2one('gamification.challenge.line', string='Challenge Line', ondelete="cascade"),
        'challenge_id': fields.related('line_id', 'challenge_id',
            string="Challenge",
            type='many2one',
            relation='gamification.challenge',
            store=True, readonly=True,
            help="Challenge that generated the goal, assign challenge to users to generate goals with a value in this field."),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),  # no start and end = always active
        'target_goal': fields.float('To Reach',
            required=True,
            track_visibility='always'),  # no goal = global index
        'current': fields.float('Current Value', required=True, track_visibility='always'),
        'completeness': fields.function(_get_completion, type='float', string='Completeness'),
        'state': fields.selection([
                ('draft', 'Draft'),
                ('inprogress', 'In progress'),
                ('reached', 'Reached'),
                ('failed', 'Failed'),
                ('canceled', 'Canceled'),
            ],
            string='State',
            required=True,
            track_visibility='always'),
        'to_update': fields.boolean('To update'),
        'closed': fields.boolean('Closed goal', help="These goals will not be recomputed."),

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
    _order = 'start_date desc, end_date desc, definition_id, id'

    def _check_remind_delay(self, cr, uid, goal, context=None):
        """Verify if a goal has not been updated for some time and send a
        reminder message of needed.

        :return: data to write on the goal object
        """
        temp_obj = self.pool['mail.template']
        if goal.remind_update_delay and goal.last_update:
            delta_max = timedelta(days=goal.remind_update_delay)
            last_update = datetime.strptime(goal.last_update, DF).date()
            if date.today() - last_update > delta_max:
                # generate a remind report
                temp_obj = self.pool.get('mail.template')
                template_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'gamification', 'email_template_goal_reminder')[0]
                template = temp_obj.get_email_template(cr, uid, template_id, goal.id, context=context)
                body_html = temp_obj.render_template(cr, uid, template.body_html, 'gamification.goal', goal.id, context=template._context)
                self.pool['mail.thread'].message_post(cr, uid, 0, body=body_html, partner_ids=[goal.user_id.partner_id.id], context=context, subtype='mail.mt_comment')
                return {'to_update': True}
        return {}

    def _get_write_values(self, cr, uid, goal, new_value, context=None):
        """Generate values to write after recomputation of a goal score"""
        if new_value == goal.current:
            # avoid useless write if the new value is the same as the old one
            return {}

        result = {goal.id: {'current': new_value}}
        if (goal.definition_id.condition == 'higher' and new_value >= goal.target_goal) \
          or (goal.definition_id.condition == 'lower' and new_value <= goal.target_goal):
            # success, do no set closed as can still change
            result[goal.id]['state'] = 'reached'

        elif goal.end_date and fields.date.today() > goal.end_date:
            # check goal failure
            result[goal.id]['state'] = 'failed'
            result[goal.id]['closed'] = True

        return result

    def update(self, cr, uid, ids, context=None):
        """Update the goals to recomputes values and change of states

        If a manual goal is not updated for enough time, the user will be
        reminded to do so (done only once, in 'inprogress' state).
        If a goal reaches the target value, the status is set to reached
        If the end date is passed (at least +1 day, time not considered) without
        the target value being reached, the goal is set as failed."""
        if context is None:
            context = {}
        commit = context.get('commit_gamification', False)

        goals_by_definition = {}
        for goal in self.browse(cr, uid, ids, context=context):
            goals_by_definition.setdefault(goal.definition_id, []).append(goal)

        for definition, goals in goals_by_definition.items():
            goals_to_write = dict((goal.id, {}) for goal in goals)
            if definition.computation_mode == 'manually':
                for goal in goals:
                    goals_to_write[goal.id].update(self._check_remind_delay(cr, uid, goal, context))
            elif definition.computation_mode == 'python':
                # TODO batch execution
                for goal in goals:
                    # execute the chosen method
                    cxt = {
                        'self': self.pool.get('gamification.goal'),
                        'object': goal,
                        'pool': self.pool,
                        'cr': cr,
                        'context': dict(context), # copy context to prevent side-effects of eval
                        'uid': uid,
                        'date': date, 'datetime': datetime, 'timedelta': timedelta, 'time': time
                    }
                    code = definition.compute_code.strip()
                    safe_eval(code, cxt, mode="exec", nocopy=True)
                    # the result of the evaluated codeis put in the 'result' local variable, propagated to the context
                    result = cxt.get('result')
                    if result is not None and type(result) in (float, int, long):
                        goals_to_write.update(
                            self._get_write_values(cr, uid, goal, result, context=context)
                        )

                    else:
                        _logger.exception(_('Invalid return content from the evaluation of code for definition %s') % definition.name)

            else:  # count or sum

                obj = self.pool.get(definition.model_id.model)
                field_date_name = definition.field_date_id and definition.field_date_id.name or False

                if definition.computation_mode == 'count' and definition.batch_mode:
                    # batch mode, trying to do as much as possible in one request
                    general_domain = safe_eval(definition.domain)
                    field_name = definition.batch_distinctive_field.name
                    subqueries = {}
                    for goal in goals:
                        start_date = field_date_name and goal.start_date or False
                        end_date = field_date_name and goal.end_date or False
                        subqueries.setdefault((start_date, end_date), {}).update({goal.id:safe_eval(definition.batch_user_expression, {'user': goal.user_id})})

                    # the global query should be split by time periods (especially for recurrent goals)
                    for (start_date, end_date), query_goals in subqueries.items():
                        subquery_domain = list(general_domain)
                        subquery_domain.append((field_name, 'in', list(set(query_goals.values()))))
                        if start_date:
                            subquery_domain.append((field_date_name, '>=', start_date))
                        if end_date:
                            subquery_domain.append((field_date_name, '<=', end_date))

                        if field_name == 'id':
                            # grouping on id does not work and is similar to search anyway
                            user_ids = obj.search(cr, uid, subquery_domain, context=context)
                            user_values = [{'id': user_id, 'id_count': 1} for user_id in user_ids]
                        else:
                            user_values = obj.read_group(cr, uid, subquery_domain, fields=[field_name], groupby=[field_name], context=context)
                        # user_values has format of read_group: [{'partner_id': 42, 'partner_id_count': 3},...]
                        for goal in [g for g in goals if g.id in query_goals.keys()]:
                            for user_value in user_values:
                                queried_value = field_name in user_value and user_value[field_name] or False
                                if isinstance(queried_value, tuple) and len(queried_value) == 2 and isinstance(queried_value[0], (int, long)):
                                    queried_value = queried_value[0]
                                if queried_value == query_goals[goal.id]:
                                    new_value = user_value.get(field_name+'_count', goal.current)
                                    goals_to_write.update(
                                        self._get_write_values(cr, uid, goal, new_value, context=context)
                                    )

                else:
                    for goal in goals:
                        # eval the domain with user replaced by goal user object
                        domain = safe_eval(definition.domain, {'user': goal.user_id})

                        # add temporal clause(s) to the domain if fields are filled on the goal
                        if goal.start_date and field_date_name:
                            domain.append((field_date_name, '>=', goal.start_date))
                        if goal.end_date and field_date_name:
                            domain.append((field_date_name, '<=', goal.end_date))

                        if definition.computation_mode == 'sum':
                            field_name = definition.field_id.name
                            # TODO for master: group on user field in batch mode
                            res = obj.read_group(cr, uid, domain, [field_name], [], context=context)
                            new_value = res and res[0][field_name] or 0.0

                        else:  # computation mode = count
                            new_value = obj.search(cr, uid, domain, context=context, count=True)

                        goals_to_write.update(
                            self._get_write_values(cr, uid, goal, new_value, context=context)
                        )

            for goal_id, value in goals_to_write.items():
                if not value:
                    continue
                self.write(cr, uid, [goal_id], value, context=context)
            if commit:
                cr.commit()
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
        context = dict(context or {})
        context['no_remind_goal'] = True
        return super(gamification_goal, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        """Overwrite the write method to update the last_update field to today

        If the current value is changed and the report frequency is set to On
        change, a report is generated
        """
        if context is None:
            context = {}
        vals['last_update'] = fields.date.today()
        result = super(gamification_goal, self).write(cr, uid, ids, vals, context=context)
        for goal in self.browse(cr, uid, ids, context=context):
            if goal.state != "draft" and ('definition_id' in vals or 'user_id' in vals):
                # avoid drag&drop in kanban view
                raise UserError(_('Can not modify the configuration of a started goal'))

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
            # open a the action linked to the goal
            action = goal.definition_id.action_id.read()[0]

            if goal.definition_id.res_id_field:
                current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
                action['res_id'] = safe_eval(goal.definition_id.res_id_field, {'user': current_user})

                # if one element to display, should see it in form mode if possible
                action['views'] = [(view_id, mode) for (view_id, mode) in action['views'] if mode == 'form'] or action['views']
            return action

        if goal.computation_mode == 'manually':
            # open a wizard window to update the value manually
            action = {
                'name': _("Update %s") % goal.definition_id.name,
                'id': goal_id,
                'type': 'ir.actions.act_window',
                'views': [[False, 'form']],
                'target': 'new',
                'context': {'default_goal_id': goal_id, 'default_current': goal.current},
                'res_model': 'gamification.goal.wizard'
            }
            return action

        return False
