# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from datetime import datetime

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

    next_occurrence_date = fields.Date()

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
            elif recurrence.repeat_type == 'number':
                name = _('Every %s %s, %s times') % (recurrence.repeat_interval, recurrence.repeat_unit, recurrence.repeat_number)
            result.append([recurrence.id, name])
        return result

    # =====================================================
    #  * Instance methods *
    # =====================================================
    def _create_occurence(self, occurence_from=False):
        raise NotImplementedError()

    def _create_occurence_values(self, occurence_from, to_template=False):
        self.ensure_one()

        fields_to_copy = occurence_from.read(self._get_recurrent_fields_to_copy()).pop()
        create_values = {
            field: value[0] if isinstance(value, tuple) else value for field, value in fields_to_copy.items()
        }

        fields_to_postpone = occurence_from.read(self._get_recurrent_fields_to_postpone()).pop()
        fields_to_postpone.pop('id', None)
        if to_template:
            create_values.update({
                field: value[0] if isinstance(value, tuple) else value for field, value in fields_to_postpone.items()
            })
            create_values['recurrence_theoretical_date'] = occurence_from.recurrence_theoretical_date or occurence_from.create_date.date()
        else:
            create_values.update({
                field: self._get_postponed_date(value, occurence_from.recurrence_theoretical_date, self.next_occurrence_date)
                for field, value in fields_to_postpone.items()
            })
            create_values['recurrence_theoretical_date'] = self.next_occurrence_date
        return create_values

    def _get_postponed_date(self, to_postpone, compared_to, applied_to):
        self.ensure_one()
        if not to_postpone:
            return False
        is_datetime = isinstance(to_postpone, datetime)
        min_time = datetime.min.time()
        if not is_datetime:
            to_postpone = datetime.combine(to_postpone, min_time)

        delta = datetime.combine(to_postpone, min_time) - datetime.combine(compared_to, min_time)
        postponed = datetime.combine(applied_to, min_time) + delta + relativedelta(
            hour=to_postpone.hour, minute=to_postpone.minute, second=to_postpone.second
        )
        return postponed if is_datetime else postponed.date()

    def _set_next_occurrence_date(self):
        today = fields.Date.today()
        for recurrence in self:
            if recurrence.repeat_type == 'number' and recurrence.recurrence_left >= 0\
                 or recurrence.repeat_type == 'until' and recurrence.repeat_until >= today\
                 or recurrence.repeat_type == 'forever':
                continue
            if recurrence.repeat_type == 'number' and recurrence.recurrence_left == 0:
                recurrence.next_occurrence_date = False
            else:
                next_date = self._get_next_occurences_dates(
                    recurrence.next_occurrence_date,
                    recurrence.repeat_interval,
                    recurrence.repeat_unit,
                    recurrence.repeat_type,
                    recurrence.repeat_until
                )
                recurrence.next_occurrence_date = next_date[0] if next_date else False
