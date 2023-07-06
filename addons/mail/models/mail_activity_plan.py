# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models
from odoo.tools.misc import groupby as tools_groupby


class MailActivityPlan(models.Model):
    _name = 'mail.activity.plan'
    _description = 'Activity Plan'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        default_res_model = self._context.get('default_res_model')
        if 'res_model_ids' in fields and default_res_model:
            res['res_model_ids'] = [(6, 0, [self.env['ir.model']._get(default_res_model).id])]
        if 'dedicated_to_res_model' in fields and default_res_model:
            res['dedicated_to_res_model'] = default_res_model
        return res

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    template_ids = fields.One2many(
        'mail.activity.plan.template', 'plan_id',
        string='Activities',
        domain="[('company_id', '=', company_id)]",
        check_company=True)
    active = fields.Boolean(default=True)
    res_model_ids = fields.Many2many('ir.model', string='Document Models', index=True,
                                     domain=[('is_mail_activity', '=', True), ('transient', '=', False)])
    dedicated_to_res_model = fields.Char(
        compute='_compute_dedicated_to_res_model', compute_sudo=True, store="True", index=True, precompute=True,
        help='Technical field used to identify plan for a specific model only.')
    steps_count = fields.Integer(compute='_compute_steps_count')
    assignation_summary = fields.Html('Assignation summary', compute='_compute_assignation')
    has_user_on_demand = fields.Boolean('Has on demand responsible', compute='_compute_assignation')

    @api.constrains('res_model_ids')
    def _check_res_model_ids_compatibility_with_templates(self):
        self.template_ids._check_activity_type_res_model()

    @api.depends('template_ids')
    def _compute_steps_count(self):
        activity_template_data = self.env['mail.activity.plan.template']._read_group([('plan_id', 'in', self.ids)], ['plan_id'], ['__count'])
        steps_count = {plan.id: count for plan, count in activity_template_data}
        for plan in self:
            plan.steps_count = steps_count.get(plan.id, 0)

    @api.depends('res_model_ids')
    def _compute_dedicated_to_res_model(self):
        for record in self:
            if len(record.res_model_ids) == 1:
                record.dedicated_to_res_model = record.res_model_ids[0].model
            else:
                record.dedicated_to_res_model = False

    @api.depends('template_ids.responsible_type', 'template_ids.summary')
    def _compute_assignation(self):
        templates_data_by_plan = dict(tools_groupby(self.env['mail.activity.plan.template'].search_read(
            [('plan_id', 'in', self.ids)],
            ['activity_type_id', 'plan_id', 'responsible_type', 'sequence', 'summary']
        ), key=lambda r: r['plan_id'][0]))
        for plan in self:
            templates_data = templates_data_by_plan.get(plan.id, False)
            if templates_data:
                formatted = ['<ul>']
                has_user_on_demand = False
                for template_data in sorted(templates_data, key=lambda d: d["sequence"]):
                    formatted.append(
                        f"<li>{template_data['activity_type_id'][1]} - {template_data['responsible_type']}" +
                        (f": {template_data['summary']}" if template_data['summary'] else '') +
                        "</li>")
                    has_user_on_demand |= template_data['responsible_type'] == 'on_demand'
                formatted.append('</ul>')
                plan.assignation_summary = ''.join(formatted)
                plan.has_user_on_demand = has_user_on_demand
            else:
                plan.assignation_summary = ''
                plan.has_user_on_demand = False

    def write(self, vals):
        dedicated_by_record_id = {r.id: r.dedicated_to_res_model for r in self if r.dedicated_to_res_model}
        res = super().write(vals)
        record_ids_by_dedicated_changed = defaultdict(list)
        for record in self:
            if record.id in dedicated_by_record_id and not record.dedicated_to_res_model:
                record_ids_by_dedicated_changed[dedicated_by_record_id[record.id]].append(record.id)
        for dedicated_changed, record_ids in record_ids_by_dedicated_changed.items():
            self.env['mail.activity.plan'].browse(record_ids)._validate_transition_from_dedicated(dedicated_changed)
        return res

    def _validate_transition_from_dedicated(self, dedicated_res_model):
        pass
