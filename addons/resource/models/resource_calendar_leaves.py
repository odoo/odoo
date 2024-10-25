# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from pytz import timezone, utc

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResourceCalendarLeaves(models.Model):
    _name = "resource.calendar.leaves"
    _description = "Resource Time Off Detail"
    _order = "date_from"

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'date_from' in fields_list and 'date_to' in fields_list and not res.get('date_from') and not res.get('date_to'):
            # Then we give the current day and we search the begin and end hours for this day in resource.calendar of the current company
            today = fields.Datetime.now()
            user_tz = timezone(self.env.user.tz or self._context.get('tz') or self.company_id.resource_calendar_id.tz or 'UTC')
            date_from = user_tz.localize(datetime.combine(today, time.min))
            date_to = user_tz.localize(datetime.combine(today, time.max))
            intervals = self.env.company.resource_calendar_id._work_intervals_batch(date_from.replace(tzinfo=utc), date_to.replace(tzinfo=utc))[False]
            if intervals:  # Then we stop and return the dates given in parameter
                list_intervals = [(start, stop) for start, stop, records in intervals]  # Convert intervals in interval list
                date_from = list_intervals[0][0]  # We take the first date in the interval list
                date_to = list_intervals[-1][1]  # We take the last date in the interval list
            res.update(
                date_from=date_from.astimezone(utc).replace(tzinfo=None),
                date_to=date_to.astimezone(utc).replace(tzinfo=None)
            )
        return res

    name = fields.Char('Reason')
    company_id = fields.Many2one(
        'res.company', string="Company", readonly=True, store=True,
        default=lambda self: self.env.company, compute='_compute_company_id')
    calendar_id = fields.Many2one(
        'resource.calendar', "Working Hours",
        compute='_compute_calendar_id', store=True, readonly=False,
        domain="[('company_id', 'in', [company_id, False])]",
        check_company=True, index=True,
    )
    date_from = fields.Datetime('Start Date', required=True)
    date_to = fields.Datetime('End Date', compute="_compute_date_to", readonly=False, required=True, store=True)
    resource_id = fields.Many2one(
        "resource.resource", 'Resource', index=True,
        help="If empty, this is a generic time off for the company. If a resource is set, the time off is only for this resource")
    time_type = fields.Selection([('leave', 'Time Off'), ('other', 'Other')], default='leave',
                                 help="Whether this should be computed as a time off or as work time (eg: formation)")

    @api.depends('resource_id.calendar_id')
    def _compute_calendar_id(self):
        for leave in self.filtered('resource_id'):
            leave.calendar_id = leave.resource_id.calendar_id

    @api.depends('calendar_id')
    def _compute_company_id(self):
        for leave in self:
            leave.company_id = leave.calendar_id.company_id or self.env.company

    @api.depends('date_from')
    def _compute_date_to(self):
        user_tz = timezone(self.env.user.tz or self._context.get('tz') or self.company_id.resource_calendar_id.tz or 'UTC')
        for leave in self:
            if not leave.date_from:
                continue
            date_to_tz = user_tz.localize(leave.date_from) + relativedelta(hour=23, minute=59, second=59)
            leave.date_to = date_to_tz.astimezone(utc).replace(tzinfo=None)

    @api.constrains('date_from', 'date_to')
    def check_dates(self):
        if self.filtered(lambda leave: leave.date_from > leave.date_to):
            raise ValidationError(_('The start date of the time off must be earlier than the end date.'))

    @api.onchange('resource_id')
    def onchange_resource(self):
        pass

    def _copy_leave_vals(self):
        self.ensure_one()
        return {
            'name': self.name,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'time_type': self.time_type,
        }
