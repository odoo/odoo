# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import logging

from datetime import date, datetime, timedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


_logger = logging.getLogger(__name__)


class GoalDefinition(models.Model):
    """Goal definition

    A goal definition contains the way to evaluate an objective
    Each module wanting to be able to set goals to the users needs to create
    a new gamification_goal_definition
    """
    _name = 'gamification.goal.definition'
    _description = 'Gamification goal definition'

    name = fields.Char(string='Goal Definition', required=True, translate=True)
    description = fields.Text(string='Goal Description')
    monetary = fields.Boolean(string='Monetary Value', help="The target and current value are defined in the company currency.")
    suffix = fields.Char(translate=True, help="The unit of the target and current values")
    full_suffix = fields.Char(compute='_compute_full_suffix', help="The currency and suffix field")
    computation_mode = fields.Selection([
            ('manually', 'Recorded manually'),
            ('count', 'Automatic: number of records'),
            ('sum', 'Automatic: sum on a field'),
            ('python', 'Automatic: execute a specific Python code'),
        ],
        string="Computation Mode",
        default='manually',
        required=True,
        help="Defined how will be computed the goals. The result of the operation will be stored in the field 'Current'.")
    display_mode = fields.Selection([
            ('progress', 'Progressive (using numerical values)'),
            ('boolean', 'Exclusive (done or not-done)'),
        ],
        string="Displayed as", required=True, default='progress')
    model_id = fields.Many2one('ir.model',
        string='Model',
        help='The model object for the field to evaluate')
    field_id = fields.Many2one('ir.model.fields',
        string='Field to Sum',
        help='The field containing the value to evaluate')
    field_date_id = fields.Many2one('ir.model.fields',
        string='Date Field',
        help='The date to use for the time period evaluated')
    domain = fields.Char(string="Filter Domain",
        required=True, default='[]',
        help="Domain for filtering records. General rule, not user depending, e.g. [('state', '=', 'done')]. The expression can contain reference to 'user' which is a browse record of the current user if not in batch mode.")

    batch_mode = fields.Boolean(string='Batch Mode',
        help="Evaluate the expression in batch instead of once for each user")
    batch_distinctive_field = fields.Many2one('ir.model.fields',
        string="Distinctive field for batch user",
        help="In batch mode, this indicates which field distinct one user form the other, e.g. user_id, partner_id...")
    batch_user_expression = fields.Char(string="Evaluted expression for batch mode",
        help="The value to compare with the distinctive field. The expression can contain reference to 'user' which is a browse record of the current user, e.g. user.id, user.partner_id.id...")
    compute_code = fields.Text(string='Python Code',
        help="Python code to be executed for each user. 'result' should contains the new current value. Evaluated user can be access through object.user_id.")
    condition = fields.Selection([
            ('higher', 'The higher the better'),
            ('lower', 'The lower the better')
        ],
        string='Goal Performance', required=True, default='higher',
        help='A goal is considered as completed when the current value is compared to the value to reach')
    action_id = fields.Many2one('ir.actions.act_window', string="Action",
        help="The action that will be called to update the goal value.")
    res_id_field = fields.Char(string="ID Field of user",
        help="The field name on the user profile (res.users) containing the value for res_id for action.")

    @api.depends('suffix', 'monetary')
    def _compute_full_suffix(self):
        for goal in self:
            if goal.suffix and not goal.monetary:
                goal.full_suffix = goal.suffix
            elif goal.monetary:
                # use the current user's company currency
                user = self.env.user
                if goal.suffix:
                    goal.full_suffix = "%s %s" % (user.company_id.currency_id.symbol, goal.suffix)
                else:
                    goal.full_suffix = user.company_id.currency_id.symbol
            else:
                goal.full_suffix = ""

    def _check_domain_validity(self):
        # take admin as should always be present
        superuser = self.env['res.users'].browse(SUPERUSER_ID)
        for definition in self.filtered(lambda definition: definition.computation_mode in ('count', 'sum')):
            Model = self.env[definition.model_id.model]
            try:
                domain = safe_eval(definition.domain, {'user': superuser})
                # demmy search to make sure the domain is valid
                Model.search_count(domain)
            except (ValueError, SyntaxError), e:
                msg = e.message or (e.msg + '\n' + e.text)
                raise UserError(_("The domain for the definition %s seems incorrect, please check it.\n\n%s") % (definition.name, msg))
        return True

    def _check_model_validity(self):
        """ make sure the selected field and model are usable"""
        for definition in self.filtered(lambda definition: definition.model_id and definition.field_id):
            try:
                Model = self.env[definition.model_id.model]
                field = Model._fields[definition.field_id.name]
                if not field.store:
                    raise UserError(
                        _("The model configuration for the definition %s seems incorrect, please check it.\n\n%s not stored") % (definition.name, definition.field_id.name))
            except KeyError, e:
                raise UserError(
                    _("The model configuration for the definition %s seems incorrect, please check it.\n\n%s not found") % (definition.name, e.message))

    @api.model
    def create(self, vals):
        definition = super(GoalDefinition, self).create(vals)
        if vals.get('computation_mode') in ('count', 'sum'):
            definition._check_domain_validity()
        if vals.get('field_id'):
            definition._check_model_validity()
        return definition

    @api.multi
    def write(self, vals):
        res = super(GoalDefinition, self).write(vals)
        if vals.get('computation_mode', 'count') in ('count', 'sum') and (vals.get('domain') or vals.get('model_id')):
            self._check_domain_validity()
        if vals.get('field_id') or vals.get('model_id') or vals.get('batch_mode'):
            self._check_model_validity()
        return res

    @api.onchange('model_id')
    def _onchange_model_id(self):
        """Force domain for the `field_id` and `field_date_id` fields"""
        if not self.model_id:
            return {'domain': {'field_id': expression.FALSE_DOMAIN, 'field_date_id': expression.FALSE_DOMAIN}}
        model_fields_domain = [('store', '=', True),
                                '|', ('model_id', '=', self.model_id.id), ('model_id', 'in', self.model_id.inherited_model_ids.ids)]
        model_date_fields_domain = expression.AND([[('ttype', 'in', ('date', 'datetime'))], model_fields_domain])
        return {'domain': {'field_id': model_fields_domain, 'field_date_id': model_date_fields_domain}}


class Goal(models.Model):
    """Goal instance for a user

    An individual goal for a user on a specified time period"""

    _name = 'gamification.goal'
    _description = 'Gamification goal instance'
    _order = 'start_date desc, end_date desc, definition_id, id'

    definition_id = fields.Many2one('gamification.goal.definition', string='Goal Definition', required=True, ondelete="cascade")
    user_id = fields.Many2one('res.users', string='User', required=True, auto_join=True, ondelete="cascade")
    line_id = fields.Many2one('gamification.challenge.line', string='Challenge Line', ondelete="cascade")
    challenge_id = fields.Many2one('gamification.challenge', related='line_id.challenge_id',
        string="Challenge",
        store=True, readonly=True,
        help="Challenge that generated the goal, assign challenge to users to generate goals with a value in this field.")
    start_date = fields.Date(string='Start Date', default=fields.Date.today)
    end_date = fields.Date(string='End Date')  # no start and end = always active
    target_goal = fields.Float(string='To Reach',
        required=True,
        track_visibility='always')  # no goal = global index
    current = fields.Float(string='Current Value', required=True, track_visibility='always', default=0)
    completeness = fields.Float(compute='_compute_completion')
    state = fields.Selection([
            ('draft', 'Draft'),
            ('inprogress', 'In progress'),
            ('reached', 'Reached'),
            ('failed', 'Failed'),
            ('canceled', 'Canceled'),
        ],
        default='draft',
        required=True,
        track_visibility='always')
    to_update = fields.Boolean()
    closed = fields.Boolean(string='Closed goal', help="These goals will not be recomputed.")

    computation_mode = fields.Selection([
            ('manually', 'Recorded manually'),
            ('count', 'Automatic: number of records'),
            ('sum', 'Automatic: sum on a field'),
            ('python', 'Automatic: execute a specific Python code'),
        ],
        related='definition_id.computation_mode')
    remind_update_delay = fields.Integer(string='Remind delay',
        help="The number of days after which the user assigned to a manual goal will be reminded. Never reminded if no value is specified.")
    last_update = fields.Date(
        help="In case of manual goal, reminders are sent if the goal as not been updated for a while (defined in challenge). Ignored in case of non-manual goal or goal not linked to a challenge.")

    definition_description = fields.Text(related='definition_id.description', string='Definition Description', readonly=True)
    definition_condition = fields.Selection([
            ('higher', 'The higher the better'),
            ('lower', 'The lower the better')
        ], related='definition_id.condition', string='Definition Condition', readonly=True)
    definition_suffix = fields.Char(related='definition_id.full_suffix', string="Suffix", readonly=True)
    definition_display = fields.Selection([
            ('progress', 'Progressive (using numerical values)'),
            ('boolean', 'Exclusive (done or not-done)'),
        ], related='definition_id.display_mode', string="Display Mode", readonly=True)

    @api.depends('definition_condition', 'current', 'target_goal')
    def _compute_completion(self):
        """Return the percentage of completeness of the goal, between 0 and 100"""
        for goal in self:
            if goal.definition_condition == 'higher':
                if goal.current >= goal.target_goal:
                    goal.completeness = 100.0
                else:
                    goal.completeness = round(100.0 * goal.current / goal.target_goal, 2)
            elif goal.current < goal.target_goal:
                # a goal 'lower than' has only two values possible: 0 or 100%
                goal.completeness = 100.0
            else:
                goal.completeness = 0.0

    @api.onchange('definition_id')
    def on_change_definition_id(self):
        self.computation_mode = self.definition_id.computation_mode
        self.definition_condition = self.definition_id.condition

    def _check_remind_delay(self):
        """Verify if a goal has not been updated for some time and send a
        reminder message of needed.

        :return: data to write on the goal object
        """
        self.ensure_one()
        if self.remind_update_delay and self.last_update:
            delta_max = timedelta(days=self.remind_update_delay)
            last_update = fields.Date.from_string(self.last_update)
            if date.today() - last_update > delta_max:
                # generate a remind report
                template = self.env.ref('gamification.email_template_goal_reminder').get_email_template(self.id)
                body_html = self.env['mail.template'].with_context(template._context).render_template(template.body_html, 'gamification.goal', self.id)
                self.browse().message_post(body=body_html, partner_ids=self.user_id.partner_id.ids, subtype='mail.mt_comment')
                return {'to_update': True}
        return {}

    def _get_write_values(self, new_value):
        """Generate values to write after recomputation of a goal score"""
        self.ensure_one()
        if new_value == self.current:
            # avoid useless write if the new value is the same as the old one
            return {}

        result = {self.id: {'current': new_value}}
        if (self.definition_id.condition == 'higher' and new_value >= self.target_goal) \
          or (self.definition_id.condition == 'lower' and new_value <= self.target_goal):
            # success, do no set closed as can still change
            result[self.id]['state'] = 'reached'

        elif self.end_date and fields.Date.today() > self.end_date:
            # check goal failure
            result[self.id]['state'] = 'failed'
            result[self.id]['closed'] = True

        return result

    @api.multi
    def update_goal(self):
        """Update the goals to recomputes values and change of states

        If a manual goal is not updated for enough time, the user will be
        reminded to do so (done only once, in 'inprogress' state).
        If a goal reaches the target value, the status is set to reached
        If the end date is passed (at least +1 day, time not considered) without
        the target value being reached, the goal is set as failed."""
        commit = self._context.get('commit_gamification')

        goals_by_definition = {}
        for goal in self:
            goals_by_definition.setdefault(goal.definition_id, []).append(goal)

        for definition, goals in goals_by_definition.items():
            goals_to_write = dict((goal.id, {}) for goal in goals)
            if definition.computation_mode == 'manually':
                for goal in goals:
                    goals_to_write[goal.id].update(goal._check_remind_delay())
            elif definition.computation_mode == 'python':
                # TODO batch execution
                for goal in goals:
                    # execute the chosen method
                    cxt = {
                        'env': self.env,
                        'model': self.env['gamification.goal'],
                        'record': goal,
                        'date': date, 'datetime': datetime, 'timedelta': timedelta, 'time': time,
                        # Backward compatibility
                        'self': self.pool.get('gamification.goal'),
                        'object': goal,
                        'pool': self.pool,
                        'cr': self._cr,
                        'context': dict(self._context), # copy context to prevent side-effects of eval
                        'uid': self._uid,
                    }
                    code = definition.compute_code.strip()
                    safe_eval(code, cxt, mode="exec", nocopy=True)
                    # the result of the evaluated codeis put in the 'result' local variable, propagated to the context
                    result = cxt.get('result')
                    if result is not None and type(result) in (float, int, long):
                        goals_to_write.update(
                            goal._get_write_values(result)
                        )

                    else:
                        _logger.exception(_('Invalid return content from the evaluation of code for definition %s') % definition.name)

            else:  # count or sum

                Model = self.env[definition.model_id.model]
                field_date_name = definition.field_date_id.name

                if definition.computation_mode == 'count' and definition.batch_mode:
                    # batch mode, trying to do as much as possible in one request
                    general_domain = safe_eval(definition.domain)
                    field_name = definition.batch_distinctive_field.name
                    subqueries = {}
                    for goal in goals:
                        start_date = field_date_name and goal.start_date or False
                        end_date = field_date_name and goal.end_date or False
                        subqueries.setdefault((start_date, end_date), {}).update({goal.id: safe_eval(definition.batch_user_expression, {'user': goal.user_id})})

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
                            users = Model.search(subquery_domain)
                            user_values = [{'id': user.id, 'id_count': 1} for user in users]
                        else:
                            user_values = Model.read_group(subquery_domain, fields=[field_name], groupby=[field_name])
                        # user_values has format of read_group: [{'partner_id': 42, 'partner_id_count': 3},...]
                        for goal in [g for g in goals if g.id in query_goals.keys()]:
                            for user_value in user_values:
                                queried_value = field_name in user_value and user_value[field_name] or False
                                if isinstance(queried_value, tuple) and len(queried_value) == 2 and isinstance(queried_value[0], (int, long)):
                                    queried_value = queried_value[0]
                                if queried_value == query_goals[goal.id]:
                                    new_value = user_value.get(field_name+'_count', goal.current)
                                    goals_to_write.update(
                                        goal._get_write_values(new_value)
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
                            res = Model.read_group(domain, [field_name], [])
                            new_value = res and res[0][field_name] or 0.0

                        else:  # computation mode = count
                            new_value = Model.search(domain, count=True)

                        goals_to_write.update(
                            goal._get_write_values(new_value)
                        )

            for goal_id, value in goals_to_write.items():
                if not value:
                    continue
                self.browse(goal_id).write(value)
            if commit:
                self._cr.commit()
        return True

    @api.multi
    def action_start(self):
        """Mark a goal as started.

        This should only be used when creating goals manually (in draft state)"""
        self.write({'state': 'inprogress'})
        return self.update_goal()

    @api.multi
    def action_reach(self):
        """Mark a goal as reached.

        If the target goal condition is not met, the state will be reset to In
        Progress at the next goal update until the end date."""
        return self.write({'state': 'reached'})

    @api.multi
    def action_fail(self):
        """Set the state of the goal to failed.

        A failed goal will be ignored in future checks."""
        return self.write({'state': 'failed'})

    @api.multi
    def action_cancel(self):
        """Reset the completion after setting a goal as reached or failed.

        This is only the current state, if the date and/or target criterias
        match the conditions for a change of state, this will be applied at the
        next goal update."""
        return self.write({'state': 'inprogress'})

    @api.model
    def create(self, vals):
        """Overwrite the create method to add a 'no_remind_goal' field to True"""
        return super(Goal, self.with_context(no_remind_goal=True)).create(vals)

    @api.multi
    def write(self, vals):
        """Overwrite the write method to update the last_update field to today

        If the current value is changed and the report frequency is set to On
        change, a report is generated
        """
        vals['last_update'] = fields.Date.today()
        result = super(Goal, self).write(vals)
        for goal in self:
            if goal.state != "draft" and ('definition_id' in vals or 'user_id' in vals):
                # avoid drag&drop in kanban view
                raise UserError(_('Can not modify the configuration of a started goal'))

            if vals.get('current'):
                if 'no_remind_goal' in self._context:
                    # new goals should not be reported
                    continue

                if goal.challenge_id.report_message_frequency == 'onchange':
                    goal.challenge_id.sudo().report_progress(users=goal.user_id)
        return result
