# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import logging
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.addons.mail.tools.parser import parse_res_ids
from odoo.exceptions import ValidationError
from odoo.tools import html2plaintext
from odoo.tools.misc import clean_context, format_date
from odoo.osv import expression
_logger = logging.getLogger(__name__)

class MailActivitySchedule(models.TransientModel):
    _name = 'mail.activity.schedule'
    _description = 'Activity schedule plan Wizard'
    _batch_size = 500

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        active_res_ids = parse_res_ids(context.get('active_ids'), self.env)
        if 'res_ids' in fields_list:
            if active_res_ids and len(active_res_ids) <= self._batch_size:
                res['res_ids'] = f"{context['active_ids']}"
            elif not active_res_ids and context.get('active_id'):
                res['res_ids'] = f"{[context['active_id']]}"
        res_model = context.get('active_model') or context.get('params', {}).get('active_model', False)
        if 'res_model' in fields_list:
            res['res_model'] = res_model
        return res

    res_model_id = fields.Many2one(
        'ir.model', string="Applies to",
        compute="_compute_res_model_id", compute_sudo=True,
        ondelete="cascade", precompute=True, readonly=False, required=False, store=True)
    res_model = fields.Char("Model", readonly=False, required=False)
    res_ids = fields.Text(
        'Document IDs', compute='_compute_res_ids',
        readonly=False, store=True, precompute=True)
    is_batch_mode = fields.Boolean('Use in batch', compute='_compute_is_batch_mode')
    company_id = fields.Many2one('res.company', 'Company',
                                 compute='_compute_company_id', required=True)
    # usage
    error = fields.Html(compute='_compute_error')
    has_error = fields.Boolean(compute='_compute_error')
    # plan-based
    plan_available_ids = fields.Many2many('mail.activity.plan', compute='_compute_plan_available_ids',
                                          store=True, compute_sudo=True)
    plan_id = fields.Many2one('mail.activity.plan', domain="[('id', 'in', plan_available_ids)]",
                              compute='_compute_plan_id', store=True, readonly=False)
    plan_has_user_on_demand = fields.Boolean(related="plan_id.has_user_on_demand")
    plan_schedule_line_ids = fields.One2many(compute='_compute_plan_schedule_line_ids', comodel_name='mail.activity.schedule.line', inverse_name='activity_schedule_id')
    plan_on_demand_user_id = fields.Many2one(
        'res.users', 'Assigned To',
        help='Choose assignation for activities with on demand assignation.',
        default=lambda self: self.env.user)
    plan_date = fields.Date(
        'Plan Date', compute='_compute_plan_date',
        store=True, readonly=False)
    # activity-based
    activity_type_id = fields.Many2one(
        'mail.activity.type', string='Activity Type',
        compute='_compute_activity_type_id', store=True, readonly=False,
        domain="['|', ('res_model', '=', False), ('res_model', '=', res_model)]", ondelete='set null')
    activity_category = fields.Selection(related='activity_type_id.category', readonly=True)
    date_deadline = fields.Date(
        'Due Date', compute="_compute_date_deadline",
        readonly=False, store=True)
    summary = fields.Char(
        'Summary', compute="_compute_summary",
        readonly=False, store=True)
    note = fields.Html(
        'Note', compute="_compute_note",
        readonly=False, store=True, sanitize_style=True)
    activity_user_id = fields.Many2one(
        'res.users', 'Assigned to', compute='_compute_activity_user_id',
        readonly=False, store=True)
    chaining_type = fields.Selection(related='activity_type_id.chaining_type', readonly=True)

    @api.depends('res_model')
    def _compute_res_model_id(self):
        self.res_model_id = False
        for scheduler in self.filtered('res_model'):
            scheduler.res_model_id = self.env['ir.model']._get_id(scheduler.res_model)

    @api.depends_context('active_ids')
    def _compute_res_ids(self):
        context = self.env.context
        for scheduler in self.filtered(lambda scheduler: not scheduler.res_ids):
            active_res_ids = parse_res_ids(context.get('active_ids'), self.env)
            if active_res_ids and len(active_res_ids) <= self._batch_size:
                scheduler.res_ids = f"{context['active_ids']}"
            elif not active_res_ids and context.get('active_id'):
                scheduler.res_ids = f"{[context['active_id']]}"

    @api.depends('res_model_id', 'res_ids')
    def _compute_company_id(self):
        for scheduler in self:
            applied_on = scheduler._get_applied_on_records()
            scheduler.company_id = (applied_on and 'company_id' in applied_on[0]._fields and applied_on[0].company_id
                                    ) or self.env.company

    @api.depends('company_id', 'res_model_id', 'res_ids',
                 'plan_id', 'plan_on_demand_user_id', 'plan_available_ids',  # plan specific
                 'activity_type_id', 'activity_user_id')  # activity specific
    def _compute_error(self):
        for scheduler in self:
            errors = set()
            applied_on = scheduler._get_applied_on_records()
            if applied_on and ('company_id' in scheduler.env[applied_on._name]._fields and
                               len(applied_on.mapped('company_id')) > 1):
                errors.add(_('The records must belong to the same company.'))
            if scheduler.plan_id:
                errors |= set(scheduler._check_plan_templates_error(applied_on))
                if not scheduler.res_ids:
                    errors.add(_("Can't launch a plan without a record."))
            if not scheduler.res_ids and not scheduler.activity_user_id:
                errors.add(_("Can't schedule activities without either a record or a user."))
            if errors:
                error_header = (
                    _('The plan "%(plan_name)s" cannot be launched:', plan_name=scheduler.plan_id.name) if scheduler.plan_id
                    else _('The activity cannot be launched:')
                )
                error_body = Markup('<ul>%s</ul>') % (
                    Markup().join(Markup('<li>%s</li>') % error for error in errors)
                )
                scheduler.error = f'{error_header}{error_body}'
                scheduler.has_error = True
            else:
                scheduler.error = False
                scheduler.has_error = False

    @api.depends('res_ids')
    def _compute_is_batch_mode(self):
        for scheduler in self:
            scheduler.is_batch_mode = len(scheduler._evaluate_res_ids()) > 1

    @api.depends('company_id', 'res_model_id')
    def _compute_plan_available_ids(self):
        for scheduler in self:
            scheduler.plan_available_ids = self.env['mail.activity.plan'].search(scheduler._get_plan_available_base_domain())

    @api.depends_context('plan_mode')
    @api.depends('plan_available_ids')
    def _compute_plan_id(self):
        for scheduler in self:
            if self.env.context.get('plan_mode'):
                scheduler.plan_id = scheduler.env['mail.activity.plan'].search(
                    [('id', 'in', self.plan_available_ids.ids)], order='id', limit=1)
            else:
                scheduler.plan_id = False

    @api.depends('res_model_id', 'res_ids')
    def _compute_plan_date(self):
        self.plan_date = fields.Date.context_today(self)

    @api.depends('plan_date', 'plan_id')
    def _compute_plan_schedule_line_ids(self):
        self.plan_schedule_line_ids = False
        for scheduler in self:
            if not scheduler.plan_id.template_ids:
                continue
            line_values = scheduler._get_summary_lines(scheduler.plan_id.template_ids)
            scheduler.plan_schedule_line_ids = [(0, 0, values) for values in line_values]

    @api.depends('res_model')
    def _compute_activity_type_id(self):
        for scheduler in self:
            if not scheduler.activity_type_id:
                scheduler.activity_type_id = scheduler.env['mail.activity']._default_activity_type_for_model(scheduler.res_model)

    @api.depends('activity_type_id')
    def _compute_date_deadline(self):
        for scheduler in self:
            if scheduler.activity_type_id:
                scheduler.date_deadline = scheduler.activity_type_id._get_date_deadline()
            elif not scheduler.date_deadline:
                scheduler.date_deadline = fields.Date.context_today(scheduler)

    @api.depends('activity_type_id')
    def _compute_summary(self):
        for scheduler in self:
            if scheduler.activity_type_id.summary:
                scheduler.summary = scheduler.activity_type_id.summary

    @api.depends('activity_type_id')
    def _compute_note(self):
        for scheduler in self:
            if scheduler.activity_type_id.default_note:
                scheduler.note = scheduler.activity_type_id.default_note

    @api.depends('activity_type_id')
    def _compute_activity_user_id(self):
        for scheduler in self:
            if scheduler.activity_type_id.default_user_id:
                scheduler.activity_user_id = scheduler.activity_type_id.default_user_id
            elif not scheduler.activity_user_id:
                scheduler.activity_user_id = False

    # Any writable fields that can change error computed field
    @api.constrains('res_model_id', 'res_ids',  # records (-> responsible)
                    'plan_id', 'plan_on_demand_user_id',  # plan specific
                    'activity_type_id', 'activity_user_id')  # activity specific
    def _check_consistency(self):
        for scheduler in self.filtered('error'):
            raise ValidationError(html2plaintext(scheduler.error))

    @api.constrains('res_ids')
    def _check_res_ids(self):
        """ Check res_ids is a valid list of integers (or Falsy). """
        for scheduler in self:
            scheduler._evaluate_res_ids()

    @api.readonly
    @api.model
    def get_model_options(self):
        """ Return a list of valid models for a user to define an activity on. """
        functional_models = [
            model.model
            for model in self.env['ir.model'].sudo().search(
                ['&', ('is_mail_thread', '=', True), ('transient', '=', False)]
            )
            if model.has_access('read')
        ]
        return functional_models

    # ------------------------------------------------------------
    # PLAN-BASED SCHEDULING API
    # ------------------------------------------------------------

    def action_schedule_plan(self):
        applied_on = self._get_applied_on_records()
        for record in applied_on:
            body = _('The plan "%(plan_name)s" has been started', plan_name=self.plan_id.name)
            activity_descriptions = []
            for template in self._plan_filter_activity_templates_to_schedule():
                if template.responsible_type == 'on_demand':
                    responsible = self.plan_on_demand_user_id
                else:
                    responsible = template._determine_responsible(self.plan_on_demand_user_id, record)['responsible']
                date_deadline = template._get_date_deadline(self.plan_date)
                record.activity_schedule(
                    activity_type_id=template.activity_type_id.id,
                    automated=False,
                    summary=template.summary,
                    note=template.note,
                    user_id=responsible.id,
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

        if len(applied_on) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': self.res_model,
                'res_id': applied_on.id,
                'name': applied_on.display_name,
                'view_mode': 'form',
                'views': [(False, "form")],
            }

        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'name': _('Launch Plans'),
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('id', 'in', applied_on.ids)],
        }

    def _check_plan_templates_error(self, applied_on):
        self.ensure_one()
        return filter(
            None, [
                activity_template._determine_responsible(self.plan_on_demand_user_id, record)['error']
                for activity_template in self.plan_id.template_ids
                for record in applied_on
            ]
        )

    # ------------------------------------------------------------
    # ACTIVITY-BASED SCHEDULING API
    # ------------------------------------------------------------

    def action_schedule_activities(self):
        self._action_schedule_activities()

    def action_schedule_activities_done(self):
        self._action_schedule_activities().action_done()

    # todo guce postfreeze: delete
    def action_schedule_activities_done_and_schedule(self):
        ctx = dict(
            clean_context(self.env.context),
            default_previous_activity_type_id=self.activity_type_id.id,
            activity_previous_deadline=self.date_deadline,
            default_res_ids=self.res_ids,
            default_res_model=self.res_model,
        )
        _messages, next_activities = self._action_schedule_activities()._action_done()
        if next_activities:
            return False
        return {
            'name': _("Schedule Activity On Selected Records") if self.is_batch_mode else _("Schedule Activity"),
            'context': ctx,
            'view_mode': 'form',
            'res_model': 'mail.activity.schedule',
            'views': [(False, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def _action_schedule_activities(self):
        if not self.res_model:
            return self.activity_schedule_no_record(
                activity_type_id=self.activity_type_id.id,
                automated=False,
                summary=self.summary,
                note=self.note,
                user_id=self.activity_user_id.id,
                date_deadline=self.date_deadline
            )
        return self._get_applied_on_records().activity_schedule(
            activity_type_id=self.activity_type_id.id,
            automated=False,
            summary=self.summary,
            note=self.note,
            user_id=self.activity_user_id.id,
            date_deadline=self.date_deadline
        )

    def activity_schedule_no_record(self, date_deadline=None, summary='', note='', **act_values):
        """ Schedule an activity on no record.
        This is a simplified version of the method present on mail.activity.mixin,
        as there is no need to apply the activity to a record.

        Note that an activity without a linked record requires an user_id; otherwise,
        no one would be able to access the activities without administrator access!

        Note that unless specified otherwise in act_values, the activities created
        will have their "automated" field set to True.

        :param date_deadline: the day the activity must be scheduled on
        the timezone of the user must be considered to set the correct deadline
        """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        if not date_deadline:
            date_deadline = fields.Date.context_today(self)
        if isinstance(date_deadline, datetime):
            _logger.warning("Scheduled deadline should be a date (got %s)", date_deadline)
        activity_type_id = act_values.get('activity_type_id', False)
        activity_type = self.env['mail.activity.type'].browse(activity_type_id) if activity_type_id else self.env['mail.activity.type']
        create_vals_list = []
        create_vals = {
            'activity_type_id': activity_type.id,
            'summary': summary or activity_type.summary,
            'automated': True,
            'note': note or activity_type.default_note,
            'date_deadline': date_deadline,
        }
        create_vals.update(act_values)
        create_vals_list.append(create_vals)
        return self.env['mail.activity'].create(create_vals_list)

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _evaluate_res_ids(self):
        """ Parse composer res_ids, which can be: an already valid list or
        tuple (generally in code), a list or tuple as a string (coming from
        actions). Void strings / missing values are evaluated as an empty list.

        :return: a list of IDs (empty list in case of falsy strings)"""
        self.ensure_one()
        return parse_res_ids(self.res_ids, self.env) or []

    def _get_applied_on_records(self):
        if not self.res_model:
            return []
        return self.env[self.res_model].browse(self._evaluate_res_ids())

    def _get_plan_available_base_domain(self):
        self.ensure_one()
        return expression.AND([
            ['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)],
            ['|', ('res_model', '=', False), ('res_model', '=', self.res_model)],
            [('template_ids', '!=', False)],  # exclude plan without activities
        ])

    def _plan_filter_activity_templates_to_schedule(self):
        return self.plan_id.template_ids

    def _get_summary_lines(self, templates):
        self.ensure_one()
        line_values = []
        for template in templates:
            newline = {
                'line': template.summary or template.activity_type_id.name,
                'summary_user_id': template.responsible_id or False,
            }
            if self.plan_date:
                newline['summary_date_deadline'] = template._get_date_deadline(self.plan_date)
            line_values.append(newline)
            activity_type = template.activity_type_id

            # Triggered next activities
            if activity_type.triggered_next_type_id:
                newline = {
                    'line': activity_type.triggered_next_type_id.summary or activity_type.triggered_next_type_id.name,
                    'summary_user_id': activity_type.triggered_next_type_id.default_user_id or False
                }
                if self.plan_date:
                    newline['summary_date_deadline'] = activity_type.triggered_next_type_id._get_date_deadline() + (self.plan_date - fields.Date.context_today(self))
                line_values.append(newline)
            # Suggested next activities
            elif activity_type.suggested_next_type_ids:
                for suggested in activity_type.suggested_next_type_ids:
                    newline = {
                        'line': suggested.summary or suggested.name,
                        'summary_user_id': suggested.default_user_id or False,
                    }
                    if self.plan_date:
                        newline['summary_date_deadline'] = suggested._get_date_deadline() + (self.plan_date - fields.Date.context_today(self))
                    line_values.append(newline)
        return line_values


class MailActivityScheduleSummary(models.TransientModel):
    _name = 'mail.activity.schedule.line'
    _description = 'Mail Activity Schedule Line'
    _order = 'id desc'
    _rec_name = 'activity_schedule_id'
    activity_schedule_id = fields.Many2one('mail.activity.schedule', required=True, ondelete='cascade')

    line = fields.Char()
    summary_date_deadline = fields.Date()
    summary_user_id = fields.Many2one('res.users')
