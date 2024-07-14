# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import get_timedelta
from odoo.exceptions import ValidationError


class PlanningRecurrency(models.Model):
    _name = 'planning.recurrency'
    _description = "Planning Recurrence"

    slot_ids = fields.One2many('planning.slot', 'recurrency_id', string="Related Planning Entries")
    repeat_interval = fields.Integer("Repeat Every", default=1, required=True)
    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='week', required=True)
    repeat_type = fields.Selection([('forever', 'Forever'), ('until', 'Until'), ('x_times', 'Number of Repetitions')], string='Weeks', default='forever')
    repeat_until = fields.Datetime(string="Repeat Until", help="Up to which date should the plannings be repeated")
    repeat_number = fields.Integer(string="Repetitions", help="No Of Repetitions of the plannings")
    last_generated_end_datetime = fields.Datetime("Last Generated End Date", readonly=True)
    company_id = fields.Many2one('res.company', string="Company", readonly=True, required=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('check_repeat_interval_positive', 'CHECK(repeat_interval >= 1)', 'The recurrence should be greater than 0.'),
        ('check_until_limit', "CHECK((repeat_type = 'until' AND repeat_until IS NOT NULL) OR (repeat_type != 'until'))", 'A recurrence repeating itself until a certain date must have its limit set'),
    ]

    @api.constrains('repeat_number', 'repeat_type')
    def _check_repeat_number(self):
        if self.filtered(lambda t: t.repeat_type == 'x_times' and t.repeat_number < 0):
            raise ValidationError(_('The number of repetitions cannot be negative.'))

    @api.constrains('company_id', 'slot_ids')
    def _check_multi_company(self):
        for recurrency in self:
            if any(recurrency.company_id != planning.company_id for planning in recurrency.slot_ids):
                raise ValidationError(_('An shift must be in the same company as its recurrency.'))

    @api.depends('repeat_type', 'repeat_interval', 'repeat_until')
    def _compute_display_name(self):
        for recurrency in self:
            if recurrency.repeat_type == 'forever':
                name = _('Forever, every %s week(s)', recurrency.repeat_interval)
            else:
                name = _('Every %s week(s) until %s', recurrency.repeat_interval, recurrency.repeat_until)
            recurrency.display_name = name

    @api.model
    def _cron_schedule_next(self):
        companies = self.env['res.company'].search([])
        now = fields.Datetime.now()
        stop_datetime = None
        for company in companies:
            delta = get_timedelta(company.planning_generation_interval, 'month')

            recurrencies = self.search([
                '&',
                '&',
                ('company_id', '=', company.id),
                ('last_generated_end_datetime', '<', now + delta),
                '|',
                ('repeat_until', '=', False),
                ('repeat_until', '>', now - delta),
            ])
            recurrencies._repeat_slot(now + delta)

    def _repeat_slot(self, stop_datetime=False):
        PlanningSlot = self.env['planning.slot']
        for recurrency in self:
            slot = PlanningSlot.search([('recurrency_id', '=', recurrency.id)], limit=1, order='start_datetime DESC')

            if slot:
                # find the end of the recurrence
                recurrence_end_dt = False
                if recurrency.repeat_type == 'until':
                    recurrence_end_dt = recurrency.repeat_until
                if recurrency.repeat_type == 'x_times':
                    recurrence_end_dt = recurrency._get_recurrence_last_datetime()

                # find end of generation period (either the end of recurrence (if this one ends before the cron period), or the given `stop_datetime` (usually the cron period))
                recurrency_stop_datetime = stop_datetime or PlanningSlot._add_delta_with_dst(
                    fields.Datetime.now(),
                    get_timedelta(recurrency.company_id.planning_generation_interval, 'month')
                )
                range_limit = min([dt for dt in [recurrence_end_dt, recurrency_stop_datetime] if dt])
                slot_duration = slot.end_datetime - slot.start_datetime

                def get_all_next_starts():
                    for i in range(1, 365 * 5): # 5 years if every day
                        next_start = PlanningSlot._add_delta_with_dst(
                            slot.start_datetime,
                            get_timedelta(recurrency.repeat_interval * i, recurrency.repeat_unit)
                        )
                        if next_start >= range_limit:
                            return
                        yield next_start

                # generate recurring slots
                resource = recurrency.slot_ids.resource_id[-1:]
                occurring_slots = PlanningSlot.search_read([
                    ('resource_id', '=', resource.id),
                    ('company_id', '=', resource.company_id.id),
                    ('end_datetime', '>=', slot.start_datetime),
                    ('start_datetime', '<=', range_limit)
                ], ['start_datetime', 'end_datetime'])

                slot_values_list = []
                for next_start in get_all_next_starts():
                    next_end = next_start + slot_duration
                    slot_values = slot.copy_data({
                        'start_datetime': next_start,
                        'end_datetime': next_end,
                        'recurrency_id': recurrency.id,
                        'company_id': recurrency.company_id.id,
                        'repeat': True,
                        'state': 'draft'
                    })[0]
                    if any(
                        next_start <= occurring_slot['end_datetime'] and
                        next_end >= occurring_slot['start_datetime']
                        for occurring_slot in occurring_slots
                    ):
                        slot_values['resource_id'] = False
                    slot_values_list.append(slot_values)
                if slot_values_list:
                    PlanningSlot.create(slot_values_list)
                    recurrency.write({'last_generated_end_datetime': slot_values_list[-1]['start_datetime']})

            else:
                recurrency.unlink()

    def _delete_slot(self, start_datetime):
        slots = self.env['planning.slot'].search([
            ('recurrency_id', 'in', self.ids),
            ('start_datetime', '>=', start_datetime),
            ('state', '=', 'draft'),
        ])
        slots.unlink()

    def _get_recurrence_last_datetime(self):
        self.ensure_one()
        end_datetime = self.env['planning.slot'].search_read([('recurrency_id', '=', self.id)], ['end_datetime'], order='end_datetime', limit=1)
        timedelta = get_timedelta((self.repeat_number - 1) * self.repeat_interval, self.repeat_unit)
        if timedelta.days > 999:
            raise ValidationError(_('Recurring shifts cannot be planned further than 999 days in the future. If you need to schedule beyond this limit, please set the recurrence to repeat forever instead.'))
        return end_datetime[0]['end_datetime'] + timedelta
