# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import AccessError


class MailActivityPlan(models.Model):
    _name = 'mail.activity.plan'
    _description = 'Activity Plan'
    _order = 'id DESC'

    def _get_model_selection(self):
        return [
            (model.model, model.name)
            for model in self.env['ir.model'].sudo().search(
                ['&', ('is_mail_activity', '=', True), ('transient', '=', False)])
        ]

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company')
    user_ids = fields.Many2many("res.users", string="Users", help="Users who can use this activity plan")
    template_ids = fields.One2many(
        'mail.activity.plan.template', 'plan_id', string='Activities',
        copy=True)
    active = fields.Boolean(default=True)
    res_model_id = fields.Many2one(
        'ir.model', string='Applies to',
        compute="_compute_res_model_id", compute_sudo=True,
        ondelete="cascade", precompute=True, readonly=False, required=True, store=True)
    res_model = fields.Selection(
        selection=_get_model_selection, string="Model", required=True,
        help='Specify a model if the activity should be specific to a model'
              ' and not available when managing activities for other models.')
    steps_count = fields.Integer(compute='_compute_steps_count')
    has_user_on_demand = fields.Boolean('Has on demand responsible', compute='_compute_has_user_on_demand')

    @api.depends('res_model')
    def _compute_res_model_id(self):
        for plan in self:
            if plan.res_model:
                # New records may not have the required "res_model" field set yet
                # (in onchange)
                plan.res_model_id = self.env['ir.model']._get_id(plan.res_model)
            else:
                plan.res_model_id = False

    @api.constrains('res_model')
    def _check_res_model_compatibility_with_templates(self):
        self.template_ids._check_activity_type_res_model()

    @api.depends('template_ids')
    def _compute_steps_count(self):
        for plan in self:
            plan.steps_count = len(plan.template_ids)

    @api.depends('template_ids.responsible_type')
    def _compute_has_user_on_demand(self):
        self.has_user_on_demand = False
        for plan in self.filtered('template_ids'):
            plan.has_user_on_demand = any(template.responsible_type == 'on_demand' for template in plan.template_ids)

    def write(self, vals):
        if any(not plan.has_access("write") and len(plan.user_ids) > 1 and self.env.user in plan.user_ids for plan in self):
            # don't let the access error in the super to show the reason
            raise AccessError(self.env._("Uh oh! Shared plans are only editable by their owners."))

        res = super().write(vals)
        if vals.keys() & {'res_model', 'user_ids'}:
            # the create access should be after the write, so a normal user
            # cannot create a plan with user_ids empty (visible for all users)
            self.check_access('create')
        return res
