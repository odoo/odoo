# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, exceptions
from odoo.tools.safe_eval import safe_eval

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
    model_id = fields.Many2one('ir.model', string='Model', ondelete='cascade')
    model_inherited_ids = fields.Many2many('ir.model', related='model_id.inherited_model_ids')
    field_id = fields.Many2one(
        'ir.model.fields', string='Field to Sum',
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
                raise exceptions.UserError(_("The domain for the definition %s seems incorrect, please check it.\n\n%s", definition.name, msg))
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

    @api.model_create_multi
    def create(self, vals_list):
        definitions = super(GoalDefinition, self).create(vals_list)
        definitions.filtered_domain([
            ('computation_mode', 'in', ['count', 'sum']),
        ])._check_domain_validity()
        definitions.filtered_domain([
            ('field_id', '=', 'True'),
        ])._check_model_validity()
        return definitions

    def write(self, vals):
        res = super(GoalDefinition, self).write(vals)
        if vals.get('computation_mode', 'count') in ('count', 'sum') and (vals.get('domain') or vals.get('model_id')):
            self._check_domain_validity()
        if vals.get('field_id') or vals.get('model_id') or vals.get('batch_mode'):
            self._check_model_validity()
        return res
