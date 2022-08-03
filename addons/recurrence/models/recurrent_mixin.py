# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from pytz import timezone, UTC

from odoo import models, fields, api, _

class RecurrentMixin(models.AbstractModel):
    _name = 'recurrent.mixin'
    _description = 'Recurrent Mixin'
    _recurrence_model = "recurrence.mixin"

    # =====================================================
    #  * Fields *
    # =====================================================
    repeat = fields.Boolean(string="Recurrent")
    recurrence_id = fields.Many2one(_recurrence_model, copy=False)
    is_recurrence_template = fields.Boolean(search="_search_is_recurrence_template", compute='_compute_is_recurrence_template')

    repeat_interval = fields.Integer(string='Repeat Every', default=1, compute='_compute_repeat', readonly=False)
    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='week', compute='_compute_repeat', readonly=False)
    repeat_type = fields.Selection([
        ('forever', 'Forever'),
        ('until', 'Until'),
        ('number', 'Number of Repetitions'),
    ], string="Until", default="forever", compute='_compute_repeat', readonly=False)
    repeat_until = fields.Date(string="End Date", compute='_compute_repeat', readonly=False)
    repeat_number = fields.Integer(string="Repetitions", default=1, compute='_compute_repeat', readonly=False)

    recurrence_update = fields.Selection([
        ('this', 'This task'),
        ('subsequent', 'This and future tasks'),
    ], default='this', store=False)
    recurrence_message = fields.Char(string='Next Occurences', compute='_compute_recurrence_message')
    # Technical field to be able to postpone dates when creating a new occurence
    recurrence_theoretical_date = fields.Date(string='Theoretical Date')

    # =====================================================
    #  * Static methods *
    # =====================================================
    @api.model
    def _get_recurrence_fields(self):
        return [
            'repeat_interval',
            'repeat_unit',
            'repeat_type',
            'repeat_until',
            'repeat_number',
        ]

    # =====================================================
    #  * Computes *
    # =====================================================
    @api.depends('repeat')
    def _compute_repeat(self):
        rec_fields = self._get_recurrence_fields()
        defaults = self.default_get(rec_fields)
        for task in self:
            for f in rec_fields:
                if task.recurrence_id:
                    task[f] = task.recurrence_id[f]
                else:
                    if task.repeat:
                        task[f] = defaults.get(f)
                    else:
                        task[f] = False

    def _compute_is_recurrence_template(self):
        recurrent_template_ids = {
            res['recurrent_template_id'][0] for res in
            self.env[self._recurrence_model].sudo()._read_group(
                [('recurrent_template_id', '!=', False), ('id', 'in', self.recurrence_id.ids)],
                ['recurrent_template_id'], ['recurrent_template_id']
            )
        }
        for recurrent in self:
            recurrent.is_recurrence_template = recurrent.id in recurrent_template_ids

    def _search_is_recurrence_template(self, operator, value):
        if operator not in ['=', '!=']:
            raise NotImplementedError('This operator %s is not supported in this search method.' % operator)
        recurrent_template_ids = [
            res['recurrent_template_id'][0] for res in
            self.env['project.task.recurrence'].sudo()._read_group(
                [('recurrent_template_id', '!=', False)],
                ['recurrent_template_id'], ['recurrent_template_id']
            )
        ]
        return [('id', 'in' if (operator == '=') == value else 'not in', recurrent_template_ids)]

    @api.depends(
        'repeat',
        'repeat_interval',
        'repeat_unit',
        'repeat_type',
        'repeat_until',
        'repeat_number'
    )
    def _compute_recurrence_message(self):
        self.recurrence_message = False
        for recurrent in self:
            if not recurrent.repeat:
                continue
            recurrence_left = recurrent.recurrence_id.recurrence_left if recurrent.recurrence_id else recurrent.repeat_number
            number_occurrences = min(5, recurrence_left if recurrent.repeat_type == 'number' else 5)
            recurring_dates = self.env[self._recurrence_model]._get_next_occurences_dates(
                recurrent.recurrence_theoretical_date or fields.Date.today() + relativedelta(**{
                    f"{recurrent.repeat_unit}s": recurrent.repeat_interval
                }),
                recurrent.repeat_interval,
                recurrent.repeat_unit,
                recurrent.repeat_type,
                recurrent.repeat_until,
                count=number_occurrences,
            )
            if recurrence_left == 0:
                recurrence_title = _('There are no more occurrences.')
            else:
                recurrence_title = _('Next occurences:')
            recurrent.recurrence_message = '<p><span class="fa fa-check-circle"></span> %s</p><ul>' % recurrence_title
            recurrent.recurrence_message += ''.join(['<li>%s</li>' % date for date in self._get_recurrence_message_items(recurring_dates[:5])])
            if recurrent.repeat_type == 'number' and recurrence_left > 5 or recurrent.repeat_type == 'forever' or len(recurring_dates) > 5:
                recurrent.recurrence_message += '<li>...</li>'
            recurrent.recurrence_message += '</ul>'
            if recurrent.repeat_type == 'until':
                recurrent.recurrence_message += _(
                    '<p><em>Number of occurences: %(occurences_count)s</em></p>'
                ) % {'occurences_count': len(recurring_dates)}

    def _get_recurrence_message_items(self, dates):
        self.ensure_one()
        is_datetime = self._get_recurrence_message_item_is_datetime()
        recurrent_duration = self._get_recurrence_message_item_duration()

        lang = self.env['res.lang']._lang_get(self.env.user.lang)
        tz = timezone(self.env.user.tz or 'UTC')
        dt_format = lang.date_format + is_datetime * (" %s" % lang.time_format)
        def localize_format_datetime(dt):
            if is_datetime:
                dt = dt.replace(tzinfo=UTC).astimezone(tz)
            return dt.strftime(dt_format)

        return ['%s' % localize_format_datetime(date) + (
                ' 🠒 %s' % localize_format_datetime(date + recurrent_duration) if recurrent_duration else ''
            ) for date in dates
        ]

    def _get_recurrence_message_item_duration(self):
        return False

    def _get_recurrence_message_item_is_datetime(self):
        return False
