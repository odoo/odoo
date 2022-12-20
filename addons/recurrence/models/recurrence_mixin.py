# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class RecurrenceMixin(models.AbstractModel):
    _name = 'recurrence.mixin'
    _description = 'Recurrence Mixin'
    _recurrent_model = "recurrent.mixin"

    # =====================================================
    #  * Fields *
    # =====================================================
    repeat_interval = fields.Integer("Repeat Every", default=1, required=True)
    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='week', required=True)
    repeat_type = fields.Selection([
        ('forever', 'Forever'),
        ('until', 'Until'),
        ('number', 'Number of Repetitions'),
    ], string='Until', default='forever')
    repeat_until = fields.Date(string="End Date")
    repeat_number = fields.Integer(string="Repetitions")

    recurrent_template_id = fields.Many2one(_recurrent_model)
    recurrent_ids = fields.One2many(_recurrent_model, 'recurrence_id')

    # =====================================================
    #  * Static methods *
    # =====================================================
    @api.model
    def _get_recurrent_fields_to_copy(self):
        return [
            'repeat',
            'recurrence_id',
        ]

    @api.model
    def _get_recurrent_fields_to_postpone(self):
        return []

    @api.model
    def _get_next_occurences_dates(
        self,
        start_datetime,
        repeat_interval,
        repeat_unit,
        repeat_type,
        repeat_until,
        count=1
    ):
        dates = []

        if repeat_type == 'until':
            repeat_until = repeat_until or fields.Date.today()

        next_datetime = start_datetime
        can_generate_date = (
            lambda: next_datetime <= repeat_until
        ) if repeat_type == 'until' else (
            lambda: len(dates) < count
        )

        while can_generate_date():
            dates.append(next_datetime)
            next_datetime = start_datetime + relativedelta(**{
                f"{repeat_unit}s": repeat_interval * len(dates)
            })

        return dates

    # =====================================================
    #  * Constrains *
    # =====================================================
    @api.constrains('repeat_interval')
    def _check_repeat_interval(self):
        if self.filtered(lambda t: t.repeat_interval < 0):
            raise ValidationError(_('The interval should be greater than 0'))

    @api.constrains('repeat_number', 'repeat_type')
    def _check_repeat_number(self):
        if self.filtered(lambda t: t.repeat_type == 'number' and t.repeat_number <= 1):
            raise ValidationError(_('Should repeat at least once'))

    @api.constrains('repeat_type', 'repeat_until')
    def _check_repeat_until(self):
        today = fields.Date.today()
        if self.filtered(lambda t: t.repeat_type == 'until' and t.repeat_until < today):
            raise ValidationError(_('The end date should be in the future'))

    # =====================================================
    #  * CRUD methods *
    # =====================================================
    def name_get(self):
        result = []
        for recurrence in self:
            if recurrence.repeat_type == 'forever':
                name = _('Forever, every %s %s') % (recurrence.repeat_interval, recurrence.repeat_unit)
            elif recurrence.repeat_type == 'until':
                name = _('Every %s %s, until %s') % (recurrence.repeat_interval, recurrence.repeat_unit, recurrence.repeat_until)
            elif recurrence.repeat_type == 'until':
                name = _('Every %s %s, %s times') % (recurrence.repeat_interval, recurrence.repeat_unit, recurrence.repeat_number)
            result.append([recurrence.id, name])
        return result

    # =====================================================
    #  * Instance methods *
    # =====================================================
    def _create_occurence(self, occurence_date):
        raise NotImplementedError()

    def _create_occurence_values(self, occurence_date):
        self.ensure_one()
        recurrent_template = self.recurrent_template_id

        fields_to_copy = recurrent_template._get_recurrent_fields_to_copy()
        template_values = recurrent_template.read(fields_to_copy).pop()
        create_values = {
            field: value[0] if isinstance(value, tuple) else value for field, value in template_values.items()
        }

        delta = occurence_date - recurrent_template.create_date.date()
        fields_to_postpone = recurrent_template._get_recurrent_fields_to_postpone()
        template_values = recurrent_template.read(fields_to_postpone).pop()
        create_values = create_values.update({
            field: self._get_postponed_date(value, delta)
            for field, value in template_values.items()
        })

        return create_values

    def _get_postponed_date(self, value, delta):
        field_is_datetime = isinstance(value, value)
        date_value = value.date() if field_is_datetime else value
        postponed_date = date_value + relativedelta(days=delta.days)
        if field_is_datetime:
            postponed_date += relativedelta(hour=value.hour, minute=value.minute, second=value.second)
        return postponed_date
