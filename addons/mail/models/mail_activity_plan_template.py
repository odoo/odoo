# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailActivityPlanTemplate(models.Model):
    _name = 'mail.activity.plan.template'
    _description = 'Activity plan template'
    _order = 'sequence, id'
    _rec_name = 'summary'

    plan_id = fields.Many2one(
        'mail.activity.plan', string="Plan",
        ondelete='cascade', required=True, index=True)
    res_model = fields.Selection(related="plan_id.res_model")
    company_id = fields.Many2one(related='plan_id.company_id')
    sequence = fields.Integer(default=10)
    activity_type_id = fields.Many2one(
        'mail.activity.type', 'Activity Type',
        default=lambda self: self.env.ref('mail.mail_activity_data_todo'),
        domain="['|', ('res_model', '=', False), '&', ('res_model', '!=', False), ('res_model', '=', parent.res_model)]",
        ondelete='restrict', required=True
    )
    # Activity type delay fields are ignored in favor of these
    delay_count = fields.Integer(
        'Interval', default=0,
        help='Number of days/week/month before executing the action after or before the scheduled plan date.')
    delay_unit = fields.Selection([
        ('days', 'days'),
        ('weeks', 'weeks'),
        ('months', 'months')],
        string="Delay units", help="Unit of delay", required=True, default='days')
    delay_from = fields.Selection([
        ('before_plan_date', 'Before Plan Date'),
        ('after_plan_date', 'After Plan Date'),
    ],
        string='Trigger', default="before_plan_date", required=True)
    icon = fields.Char('Icon', related='activity_type_id.icon', readonly=True)
    summary = fields.Char('Summary', compute="_compute_summary", store=True, readonly=False)
    responsible_type = fields.Selection([
        ('on_demand', 'Ask at launch'),
        ('other', 'Default user'),
    ], default='on_demand', string='Assignment', required=True,
        compute="_compute_responsible_type", store=True, readonly=False)
    responsible_id = fields.Many2one(
        'res.users',
        'Assigned to',
        check_company=True, compute="_compute_responsible_id", store=True, readonly=False)
    note = fields.Html('Note', compute="_compute_note", store=True, readonly=False)
    next_activity_ids = fields.Many2many(
        'mail.activity.type', string='Next Activities',
        compute='_compute_next_activity_ids', readonly=False, store=True)

    @api.constrains('activity_type_id', 'plan_id')
    def _check_activity_type_res_model(self):
        """ Check that the plan models are compatible with the template activity
        type model. Note that it depends also on "activity_type_id.res_model" and
        "plan_id.res_model". That's why this method is called by those models
        when the mentioned fields are updated.
        """
        for template in self.filtered(lambda tpl: tpl.activity_type_id.res_model):
            if template.activity_type_id.res_model != template.plan_id.res_model:
                raise ValidationError(
                    _('The activity type "%(activity_type_name)s" is not compatible with the plan "%(plan_name)s"'
                      ' because it is limited to the model "%(activity_type_model)s".',
                      activity_type_name=template.activity_type_id.name,
                      activity_type_model=template.activity_type_id.res_model,
                      plan_name=template.plan_id.name,
                     )
                )

    @api.constrains('responsible_id', 'responsible_type')
    def _check_responsible(self):
        """ Ensure that responsible_id is set when responsible is set to "other". """
        for template in self:
            if template.responsible_type == 'other' and not template.responsible_id:
                raise ValidationError(_('When selecting "Default user" assignment, you must specify a responsible.'))

    @api.depends('activity_type_id')
    def _compute_next_activity_ids(self):
        """ Update next activities only when changing activity type on template.
        Any change on type configuration should not be propagated. """
        for template in self:
            activity_type = template.activity_type_id
            if activity_type.triggered_next_type_id:
                template.next_activity_ids = activity_type.triggered_next_type_id.ids
            elif activity_type.suggested_next_type_ids:
                template.next_activity_ids = activity_type.suggested_next_type_ids.ids
            else:
                template.next_activity_ids = False

    @api.depends('activity_type_id')
    def _compute_note(self):
        for template in self:
            template.note = template.activity_type_id.default_note

    @api.depends('activity_type_id', 'responsible_type')
    def _compute_responsible_id(self):
        for template in self:
            template.responsible_id = template.activity_type_id.default_user_id
            if template.responsible_type != 'other' and template.responsible_id:
                template.responsible_id = False

    @api.depends('activity_type_id')
    def _compute_responsible_type(self):
        for template in self:
            if template.activity_type_id.default_user_id:
                template.responsible_type = 'other'
            else:
                template.responsible_type = 'on_demand'

    @api.depends('activity_type_id')
    def _compute_summary(self):
        for template in self:
            template.summary = template.activity_type_id.summary

    def _get_date_deadline(self, base_date=False):
        """ Return the deadline of the activity to be created given the base date. """
        self.ensure_one()
        base_date = base_date or fields.Date.context_today(self)
        delta = relativedelta(**{self.delay_unit: self.delay_count})
        if self.delay_from == 'after_plan_date':
            return base_date + delta
        return base_date - delta

    def _determine_responsible(self, on_demand_responsible, applied_on_record):
        """ Determine the responsible for the activity based on the template
        for the given record and on demand responsible.

        Based on the responsible_type, this method will determine the responsible
        to set on the activity for the given record (applied_on_record).
        Following the responsible_type:
        - on_demand: on_demand_responsible is used as responsible (allow to set it
        when using the template)
        - other: the responsible field is used (preset user at the template level)

        Other module can extend it and base the responsible on the record on which
        the activity will be set. Ex.: 'coach' on employee record will assign the
        coach user of the employee.

        :param <res.user> on_demand_responsible: on demand responsible
        :param recordset applied_on_record: the record on which the activity
            will be created
        :returns: {'responsible': <res.user>, error: str|False}
        :rtype: dict
        """
        self.ensure_one()
        error = False
        warning = False
        if self.responsible_type == 'other':
            responsible = self.responsible_id
        elif self.responsible_type == 'on_demand':
            responsible = on_demand_responsible
            if not responsible:
                error = _('No responsible specified for %(activity_type_name)s: %(activity_summary)s.',
                          activity_type_name=self.activity_type_id.name,
                          activity_summary=self.summary or '-')
        else:
            raise ValueError(f'Invalid responsible value {self.responsible_type}.')
        return {
            'responsible': responsible,
            'error': error,
            'warning': warning,
        }
