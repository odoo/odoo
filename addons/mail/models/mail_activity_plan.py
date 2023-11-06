# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models


class MailActivityPlan(models.Model):
    _name = 'mail.activity.plan'
    _description = 'Activity Plan'
    _order = 'id DESC'

    def _get_model_selection(self):
        return [
            (model.model, model.name)
            for model in self.env['ir.model'].sudo().search(
                ['&', ('is_mail_thread', '=', True), ('transient', '=', False)])
        ]

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    template_ids = fields.One2many(
        'mail.activity.plan.template', 'plan_id', string='Activities')
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
    assignation_summary = fields.Html('Plan Summary', compute='_compute_assignation_summary')
    has_user_on_demand = fields.Boolean('Has on demand responsible', compute='_compute_has_user_on_demand')

    @api.depends('res_model')
    def _compute_res_model_id(self):
        for plan in self:
            plan.res_model_id = self.env['ir.model']._get_id(plan.res_model)

    @api.constrains('res_model')
    def _check_res_model_compatibility_with_templates(self):
        self.template_ids._check_activity_type_res_model()

    @api.depends('template_ids')
    def _compute_steps_count(self):
        for plan in self:
            plan.steps_count = len(plan.template_ids)

    @api.depends('template_ids.summary')
    def _compute_assignation_summary(self):
        self.assignation_summary = ''
        for plan in self.filtered('template_ids'):
            summaries = [
                template.activity_type_id.name + (f": {template.summary}" if template.summary else '')
                for template in plan.template_ids
            ]
            if summaries:
                plan.assignation_summary = Markup('<ul>%s</ul>') % (
                    Markup().join(Markup('<li>%s</li>') % summary for summary in summaries)
                )
            else:
                plan.assignation_summary = ''

    @api.depends('template_ids.responsible_type')
    def _compute_has_user_on_demand(self):
        self.has_user_on_demand = False
        for plan in self.filtered('template_ids'):
            plan.has_user_on_demand = any(template.responsible_type == 'on_demand' for template in plan.template_ids)
