# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.tools.misc import format_date


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
            plan.res_model_id = self.env['ir.model']._get_id(plan.res_model)

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

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for plan, vals in zip(self, vals_list):
                vals['name'] = _("%s (copy)", plan.name)
        return vals_list

    def _get_summary_lines(self, plan_date=None):
        self.ensure_one()
        summaries = []
        for template in self.template_ids:
            activity_type = template.activity_type_id
            summary_line = activity_type.name
            if template.summary:
                summary_line += f": {template.summary}"
            # We don't display deadlines when the user doesn't specify a plan_date
            if plan_date:
                summary_line += f" ({format_date(self.env, template._get_date_deadline(plan_date))})"
            next_activities = []
            # Triggered next activity
            if activity_type.triggered_next_type_id:
                triggered_activity = activity_type.triggered_next_type_id
                triggered_delay_unit = dict(triggered_activity._fields['delay_unit']._description_selection(self.env))[triggered_activity.delay_unit]
                triggered_delay_from = dict(triggered_activity._fields['delay_from']._description_selection(self.env))[triggered_activity.delay_from]

                next_activities.append(
                    _("%(activity_name)s %(delay_count)s %(delay_unit)s %(delay_from)s",
                    activity_name=triggered_activity.name,
                    delay_count=triggered_activity.delay_count,
                    delay_unit=triggered_delay_unit,
                    delay_from=triggered_delay_from
                    )
                )
            # Suggested next activities
            elif activity_type.suggested_next_type_ids:
                suggested_activities = []
                for suggested_activity in activity_type.suggested_next_type_ids:
                    suggested_delay_unit = dict(suggested_activity._fields['delay_unit']._description_selection(self.env))[suggested_activity.delay_unit]
                    suggested_delay_from = dict(suggested_activity._fields['delay_from']._description_selection(self.env))[suggested_activity.delay_from]
                    suggested_activities.append(
                        _("%(activity_name)s %(delay_count)s %(delay_unit)s %(delay_from)s",
                        activity_name=suggested_activity.name,
                        delay_count=suggested_activity.delay_count,
                        delay_unit=suggested_delay_unit,
                        delay_from=suggested_delay_from
                        )
                    )
                next_activities.append(_(" or ").join(suggested_activities))
            # Add next activities as nested list for each activity type
            if next_activities:
                nested_summary_line = Markup('<ul>%s</ul>') % Markup().join(
                    Markup('<li>%s</li>') % activity for activity in next_activities
                )
                summary_line += nested_summary_line
            summaries.append(Markup('<li>%s</li>') % summary_line)
        return Markup('<ul>%s</ul>') % Markup().join(summaries) if summaries else ''

    def _schedule_plan(self, res_ids=[], on_demand_responsible=None, plan_date=None, activity_filter=lambda _: True):
        applied_on = self.env[self.res_model].browse(res_ids)
        for record in applied_on:
            body = _('The plan "%(plan_name)s" has been started', plan_name=self.name)
            activity_descriptions = []
            for template in self.template_ids.filtered(activity_filter):
                if template.responsible_type == 'on_demand':
                    responsible = on_demand_responsible
                else:
                    responsible = template._determine_responsible(on_demand_responsible, record)['responsible']
                date_deadline = template._get_date_deadline(plan_date)
                record.activity_schedule(
                    activity_type_id=template.activity_type_id.id,
                    automated=False,
                    summary=template.summary,
                    note=template.note,
                    user_id=responsible.id if responsible else False,
                    date_deadline=date_deadline
                )
                activity_descriptions.append(
                    _('%(activity)s, assigned to %(name)s, due on the %(deadline)s',
                      activity=template.summary or template.activity_type_id.name,
                      name=responsible.name, deadline=format_date(self.env, date_deadline)))

            if activity_descriptions:
                body += Markup('<ul>%s</ul>') % (
                    Markup().join(Markup('<li>%s</li>') % description for description in activity_descriptions)
                )
            record.message_post(body=body)

        return applied_on
