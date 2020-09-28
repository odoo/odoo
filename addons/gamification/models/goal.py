# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import logging
from datetime import date, datetime, timedelta

from odoo import api, fields, models, _, exceptions
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval, time

_logger = logging.getLogger(__name__)


DOMAIN_TEMPLATE = "[('store', '=', True), '|', ('model_id', '=', model_id), ('model_id', 'in', model_inherited_ids)%s]"
class GoalDefinition(models.Model):
    """Goal definition

    A goal definition contains the way to evaluate an objective
    Each module wanting to be able to set goals to the users needs to create
    a new gamification_goal_definition
    """
    _name = 'gamification.goal.definition'
    _description = 'Gamification Goal Definition'

    name = fields.Char("Goal Definition", required=True, translate=True)
    description = fields.Text("Goal Description")
    monetary = fields.Boolean("Monetary Value", default=False, help="The target and current value are defined in the company currency.")
    suffix = fields.Char("Suffix", help="The unit of the target and current values", translate=True)
    full_suffix = fields.Char("Full Suffix", compute='_compute_full_suffix', help="The currency and suffix field")
    computation_mode = fields.Selection([
        ('manually', "Recorded manually"),
        ('count', "Automatic: number of records"),
        ('sum', "Automatic: sum on a field"),
        ('python', "Automatic: execute a specific Python code"),
    ], default='manually', string="Computation Mode", required=True,
       help="Define how the goals will be computed. The result of the operation will be stored in the field 'Current'.")
    display_mode = fields.Selection([
        ('progress', "Progressive (using numerical values)"),
        ('boolean', "Exclusive (done or not-done)"),
    ], default='progress', string="Displayed as", required=True)
    model_id = fields.Many2one('ir.model', string='Model', help='The model object for the field to evaluate')
    model_inherited_ids = fields.Many2many('ir.model', related='model_id.inherited_model_ids')
    field_id = fields.Many2one(
        'ir.model.fields', string='Field to Sum', help='The field containing the value to evaluate',
        domain=DOMAIN_TEMPLATE % ''
    )
    field_date_id = fields.Many2one(
        'ir.model.fields', string='Date Field', help='The date to use for the time period evaluated',
        domain=DOMAIN_TEMPLATE % ", ('ttype', 'in', ('date', 'datetime'))"
    )
    domain = fields.Char(
        "Filter Domain", required=True, default="[]",
        help="Domain for filtering records. General rule, not user depending,"
             " e.g. [('state', '=', 'done')]. The expression can contain"
             " reference to 'user' which is a browse record of the current"
             " user if not in batch mode.")

    batch_mode = fields.Boolean("Batch Mode", help="Evaluate the expression in batch instead of once for each user")
    batch_distinctive_field = fields.Many2one('ir.model.fields', string="Distinctive field for batch user", help="In batch mode, this indicates which field distinguishes one user from the other, e.g. user_id, partner_id...")
    batch_user_expression = fields.Char("Evaluated expression for batch mode", help="The value to compare with the distinctive field. The expression can contain reference to 'user' which is a browse record of the current user, e.g. user.id, user.partner_id.id...")
    compute_code = fields.Text("Python Code", help="Python code to be executed for each user. 'result' should contains the new current value. Evaluated user can be access through object.user_id.")
    condition = fields.Selection([
        ('higher', "The higher the better"),
        ('lower', "The lower the better")
    ], default='higher', required=True, string="Goal Performance",
       help="A goal is considered as completed when the current value is compared to the value to reach")
    action_id = fields.Many2one('ir.actions.act_window', string="Action", help="The action that will be called to update the goal value.")
    res_id_field = fields.Char("ID Field of user", help="The field name on the user profile (res.users) containing the value for res_id for action.")

    @api.depends('suffix', 'monetary')  # also depends of user...
    def _compute_full_suffix(self):
        for goal in self:
            items = []

            if goal.monetary:
                items.append(self.env.company.currency_id.symbol or u'¤')
            if goal.suffix:
                items.append(goal.suffix)

            goal.full_suffix = u' '.join(items)

    def _check_domain_validity(self):
        # take admin as should always be present
        for definition in self:
            if definition.computation_mode not in ('count', 'sum'):
                continue

            Obj = self.env[definition.model_id.model]
            try:
                domain = safe_eval(definition.domain, {
                    'user': self.env.user.with_user(self.env.user)
                })
                # dummy search to make sure the domain is valid
                Obj.search_count(domain)
            except (ValueError, SyntaxError) as e:
                msg = e
                if isinstance(e, SyntaxError):
                    msg = (e.msg + '\n' + e.text)
                raise exceptions.UserError(_("The domain for the definition %s seems incorrect, please check it.\n\n%s") % (definition.name, msg))
        return True

    def _check_model_validity(self):
        """ make sure the selected field and model are usable"""
        for definition in self:
            try:
                if not (definition.model_id and definition.field_id):
                    continue

                Model = self.env[definition.model_id.model]
                field = Model._fields.get(definition.field_id.name)
                if not (field and field.store):
                    raise exceptions.UserError(_(
                        "The model configuration for the definition %(name)s seems incorrect, please check it.\n\n%(field_name)s not stored",
                        name=definition.name,
                        field_name=definition.field_id.name
                    ))
            except KeyError as e:
                raise exceptions.UserError(_(
                    "The model configuration for the definition %(name)s seems incorrect, please check it.\n\n%(error)s not found",
                    name=definition.name,
                    error=e
                ))

    @api.model
    def create(self, vals):
        definition = super(GoalDefinition, self).create(vals)
        if definition.computation_mode in ('count', 'sum'):
            definition._check_domain_validity()
        if vals.get('field_id'):
            definition._check_model_validity()
        return definition

    def write(self, vals):
        res = super(GoalDefinition, self).write(vals)
        if vals.get('computation_mode', 'count') in ('count', 'sum') and (vals.get('domain') or vals.get('model_id')):
            self._check_domain_validity()
        if vals.get('field_id') or vals.get('model_id') or vals.get('batch_mode'):
            self._check_model_validity()
        return res

class Goal(models.Model):
    """Goal instance for a user

    An individual goal for a user on a specified time period"""

    _name = 'gamification.goal'
    _description = 'Gamification Goal'
    _rec_name = 'definition_id'
    _order = 'start_date desc, end_date desc, definition_id, id'

    definition_id = fields.Many2one('gamification.goal.definition', string="Goal Definition", required=True, ondelete="cascade")
    user_id = fields.Many2one('res.users', string="User", required=True, auto_join=True, ondelete="cascade")
    line_id = fields.Many2one('gamification.challenge.line', string="Challenge Line", ondelete="cascade")
    challenge_id = fields.Many2one(
        related='line_id.challenge_id', store=True, readonly=True,
        help="Challenge that generated the goal, assign challenge to users "
             "to generate goals with a value in this field.")
    start_date = fields.Date("Start Date", default=fields.Date.today)
    end_date = fields.Date("End Date")  # no start and end = always active
    target_goal = fields.Float('To Reach', required=True)
# no goal = global index
    current = fields.Float("Current Value", required=True, default=0)
    completeness = fields.Float("Completeness", compute='_get_completion')
    state = fields.Selection([
        ('draft', "Draft"),
        ('inprogress', "In progress"),
        ('reached', "Reached"),
        ('failed', "Failed"),
        ('canceled', "Canceled"),
    ], default='draft', string='State', required=True)
    to_update = fields.Boolean('To update')
    closed = fields.Boolean('Closed goal', help="These goals will not be recomputed.")

    computation_mode = fields.Selection(related='definition_id.computation_mode', readonly=False)
    remind_update_delay = fields.Integer(
        "Remind delay", help="The number of days after which the user "
                             "assigned to a manual goal will be reminded. "
                             "Never reminded if no value is specified.")
    last_update = fields.Date(
        "Last Update",
        help="In case of manual goal, reminders are sent if the goal as not "
             "been updated for a while (defined in challenge). Ignored in "
             "case of non-manual goal or goal not linked to a challenge.")

    definition_description = fields.Text("Definition Description", related='definition_id.description', readonly=True)
    definition_condition = fields.Selection(string="Definition Condition", related='definition_id.condition', readonly=True)
    definition_suffix = fields.Char("Suffix", related='definition_id.full_suffix', readonly=True)
    definition_display = fields.Selection(string="Display Mode", related='definition_id.display_mode', readonly=True)

    @api.depends('current', 'target_goal', 'definition_id.condition')
    def _get_completion(self):
        """Return the percentage of completeness of the goal, between 0 and 100"""
        for goal in self:
            if goal.definition_condition == 'higher':
                if goal.current >= goal.target_goal:
                    goal.completeness = 100.0
                else:
                    goal.completeness = round(100.0 * goal.current / goal.target_goal, 2) if goal.target_goal else 0
            elif goal.current < goal.target_goal:
                # a goal 'lower than' has only two values possible: 0 or 100%
                goal.completeness = 100.0
            else:
                goal.completeness = 0.0

    def _check_remind_delay(self):
        """Verify if a goal has not been updated for some time and send a
        reminder message of needed.

        :return: data to write on the goal object
        """
        if not (self.remind_update_delay and self.last_update):
            return {}

        delta_max = timedelta(days=self.remind_update_delay)
        last_update = fields.Date.from_string(self.last_update)
        if date.today() - last_update < delta_max:
            return {}

        # generate a reminder report
        body_html = self.env.ref('gamification.email_template_goal_reminder')._render_field('body_html', self.ids, compute_lang=True)[self.id]
        self.message_notify(
            body=body_html,
            partner_ids=[self.user_id.partner_id.id],
            subtype_xmlid='mail.mt_comment',
            email_layout_xmlid='mail.mail_notification_light',
        )

        return {'to_update': True}

    def _get_write_values(self, new_value):
        """Generate values to write after recomputation of a goal score"""
        if new_value == self.current:
            # avoid useless write if the new value is the same as the old one
            return {}

        result = {'current': new_value}
        if (self.definition_id.condition == 'higher' and new_value >= self.target_goal) \
          or (self.definition_id.condition == 'lower' and new_value <= self.target_goal):
            # success, do no set closed as can still change
            result['state'] = 'reached'

        elif self.end_date and fields.Date.today() > self.end_date:
            # check goal failure
            result['state'] = 'failed'
            result['closed'] = True

        return {self: result}

    def update_goal(self):
        """Update the goals to recomputes values and change of states

        If a manual goal is not updated for enough time, the user will be
        reminded to do so (done only once, in 'inprogress' state).
        If a goal reaches the target value, the status is set to reached
        If the end date is passed (at least +1 day, time not considered) without
        the target value being reached, the goal is set as failed."""
        goals_by_definition = {}
        for goal in self.with_context(prefetch_fields=False):
            goals_by_definition.setdefault(goal.definition_id, []).append(goal)

        for definition, goals in goals_by_definition.items():
            goals_to_write = {}
            if definition.computation_mode == 'manually':
                for goal in goals:
                    goals_to_write[goal] = goal._check_remind_delay()
            elif definition.computation_mode == 'python':
                # TODO batch execution
                for goal in goals:
                    # execute the chosen method
                    cxt = {
                        'object': goal,
                        'env': self.env,

                        'date': date,
                        'datetime': datetime,
                        'timedelta': timedelta,
                        'time': time,
                    }
                    code = definition.compute_code.strip()
                    safe_eval(code, cxt, mode="exec", nocopy=True)
                    # the result of the evaluated codeis put in the 'result' local variable, propagated to the context
                    result = cxt.get('result')
                    if isinstance(result, (float, int)):
                        goals_to_write.update(goal._get_write_values(result))
                    else:
                        _logger.error(
                            "Invalid return content '%r' from the evaluation "
                            "of code for definition %s, expected a number",
                            result, definition.name)

            else:  # count or sum
                Obj = self.env[definition.model_id.model]

                field_date_name = definition.field_date_id.name
                if definition.computation_mode == 'count' and definition.batch_mode:
                    # batch mode, trying to do as much as possible in one request
                    general_domain = ast.literal_eval(definition.domain)
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
                            users = Obj.search(subquery_domain)
                            user_values = [{'id': user.id, 'id_count': 1} for user in users]
                        else:
                            user_values = Obj.read_group(subquery_domain, fields=[field_name], groupby=[field_name])
                        # user_values has format of read_group: [{'partner_id': 42, 'partner_id_count': 3},...]
                        for goal in [g for g in goals if g.id in query_goals]:
                            for user_value in user_values:
                                queried_value = field_name in user_value and user_value[field_name] or False
                                if isinstance(queried_value, tuple) and len(queried_value) == 2 and isinstance(queried_value[0], int):
                                    queried_value = queried_value[0]
                                if queried_value == query_goals[goal.id]:
                                    new_value = user_value.get(field_name+'_count', goal.current)
                                    goals_to_write.update(goal._get_write_values(new_value))

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
                            res = Obj.read_group(domain, [field_name], [])
                            new_value = res and res[0][field_name] or 0.0

                        else:  # computation mode = count
                            new_value = Obj.search_count(domain)

                        goals_to_write.update(goal._get_write_values(new_value))

            for goal, values in goals_to_write.items():
                if not values:
                    continue
                goal.write(values)
            if self.env.context.get('commit_gamification'):
                self.env.cr.commit()
        return True

    def action_start(self):
        """Mark a goal as started.

        This should only be used when creating goals manually (in draft state)"""
        self.write({'state': 'inprogress'})
        return self.update_goal()

    def action_reach(self):
        """Mark a goal as reached.

        If the target goal condition is not met, the state will be reset to In
        Progress at the next goal update until the end date."""
        return self.write({'state': 'reached'})

    def action_fail(self):
        """Set the state of the goal to failed.

        A failed goal will be ignored in future checks."""
        return self.write({'state': 'failed'})

    def action_cancel(self):
        """Reset the completion after setting a goal as reached or failed.

        This is only the current state, if the date and/or target criteria
        match the conditions for a change of state, this will be applied at the
        next goal update."""
        return self.write({'state': 'inprogress'})

    @api.model
    def create(self, vals):
        return super(Goal, self.with_context(no_remind_goal=True)).create(vals)

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
                raise exceptions.UserError(_('Can not modify the configuration of a started goal'))

            if vals.get('current') and 'no_remind_goal' not in self.env.context:
                if goal.challenge_id.report_message_frequency == 'onchange':
                    goal.challenge_id.sudo().report_progress(users=goal.user_id)
        return result

    def get_action(self):
        """Get the ir.action related to update the goal

        In case of a manual goal, should return a wizard to update the value
        :return: action description in a dictionary
        """
        if self.definition_id.action_id:
            # open a the action linked to the goal
            action = self.definition_id.action_id.read()[0]

            if self.definition_id.res_id_field:
                current_user = self.env.user.with_user(self.env.user)
                action['res_id'] = safe_eval(self.definition_id.res_id_field, {
                    'user': current_user
                })

                # if one element to display, should see it in form mode if possible
                action['views'] = [
                    (view_id, mode)
                    for (view_id, mode) in action['views']
                    if mode == 'form'
                ] or action['views']
            return action

        if self.computation_mode == 'manually':
            # open a wizard window to update the value manually
            action = {
                'name': _("Update %s", self.definition_id.name),
                'id': self.id,
                'type': 'ir.actions.act_window',
                'views': [[False, 'form']],
                'target': 'new',
                'context': {'default_goal_id': self.id, 'default_current': self.current},
                'res_model': 'gamification.goal.wizard'
            }
            return action

        return False
