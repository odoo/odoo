# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
import pytz
from datetime import datetime

class CalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    holiday_id = fields.Many2one("hr.leave", string='Leave Request')

    @api.constrains('date_from', 'date_to', 'calendar_id')
    def _check_compare_dates(self):
        all_existing_leaves = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('company_id', 'in', self.company_id.ids),
            ('date_from', '<=', max(self.mapped('date_to'))),
            ('date_to', '>=', min(self.mapped('date_from'))),
        ])
        for record in self:
            if not record.resource_id:
                existing_leaves = all_existing_leaves.filtered(lambda leave:
                        record.id != leave.id
                        and record['company_id'] == leave['company_id']
                        and record['date_from'] <= leave['date_to']
                        and record['date_to'] >= leave['date_from'])
                if record.calendar_id:
                    existing_leaves = existing_leaves.filtered(lambda l: not l.calendar_id or l.calendar_id == record.calendar_id)
                if existing_leaves:
                    raise ValidationError(_('Two public holidays cannot overlap each other for the same working hours.'))

    def _get_domain(self, time_domain_dict):
        domain = []
        for date in time_domain_dict:
            domain = expression.OR([domain, [
                    ('employee_company_id', '=', date['company_id']),
                    ('date_to', '>', date['date_from']),
                    ('date_from', '<', date['date_to'])]
            ])
        return expression.AND([domain, [('state', '!=', 'refuse'), ('active', '=', True)]])

    def _get_time_domain_dict(self):
        return [{
            'company_id' : record.company_id.id,
            'date_from' : record.date_from,
            'date_to' : record.date_to
        } for record in self if not record.resource_id]

    def _reevaluate_leaves(self, time_domain_dict):
        if not time_domain_dict:
            return

        domain = self._get_domain(time_domain_dict)
        leaves = self.env['hr.leave'].search(domain)
        if not leaves:
            return

        previous_durations = leaves.mapped('number_of_days')
        previous_states = leaves.mapped('state')
        leaves.sudo().write({
            'state': 'draft',
        })
        self.env.add_to_compute(self.env['hr.leave']._fields['number_of_days'], leaves)
        self.env.add_to_compute(self.env['hr.leave']._fields['duration_display'], leaves)
        sick_time_status = self.env.ref('hr_holidays.holiday_status_sl')
        for previous_duration, leave, state in zip(previous_durations, leaves, previous_states):
            duration_difference = previous_duration - leave.number_of_days
            if duration_difference > 0 and leave['holiday_allocation_id'] and leave.number_of_days == 0.0:
                message = _("Due to a change in global time offs, you have been granted %s day(s) back.", duration_difference)
                leave._notify_change(message)
            if leave.number_of_days > previous_duration\
                    and leave.holiday_status_id not in sick_time_status:
                new_leaves = leave.split_leave(time_domain_dict)
                leaves |= new_leaves
                previous_states += [state] * len(new_leaves)

        leaves_to_cancel = self.env['hr.leave']
        for state, leave in zip(previous_states, leaves):
            leave.write({'state': state})
            if leave.number_of_days == 0.0:
                leaves_to_cancel |= leave
            elif leave.state == 'validate':
                # recreate the resource leave that were removed by writing state to draft
                leave.sudo()._create_resource_leave()

        leaves_to_cancel._force_cancel(_("a new public holiday completely overrides this leave."), 'mail.mt_comment')

    def _convert_timezone(self, utc_naive_datetime, tz_from, tz_to):
        """
            Convert a naive date to another timezone that initial timezone
            used to generate the date.
            :param utc_naive_datetime: utc date without tzinfo
            :type utc_naive_datetime: datetime
            :param tz_from: timezone used to obtained `utc_naive_datetime`
            :param tz_to: timezone in which we want the date
            :return: datetime converted into tz_to without tzinfo
            :rtype: datetime
        """
        naive_datetime_from = utc_naive_datetime.astimezone(tz_from).replace(tzinfo=None)
        aware_datetime_to = tz_to.localize(naive_datetime_from)
        utc_naive_datetime_to = aware_datetime_to.astimezone(pytz.utc).replace(tzinfo=None)
        return utc_naive_datetime_to

    def _ensure_datetime(self, datetime_representation, date_format=None):
        """
            Be sure to get a datetime object if we have the necessary information.
            :param datetime_reprentation: object which should represent a datetime
            :rtype: datetime if a correct datetime_represtion, None otherwise
        """
        if isinstance(datetime_representation, datetime):
            return datetime_representation
        elif isinstance(datetime_representation, str) and date_format:
            return datetime.strptime(datetime_representation, date_format)
        else:
            return None

    def _prepare_public_holidays_values(self, vals_list):
        for vals in vals_list:
            # Manage the case of create a Public Time Off in another timezone
            # The datetime created has to be in UTC for the calendar's timezone
            if not vals.get('calendar_id') or vals.get('resource_id') or \
                not isinstance(vals.get('date_from'), (datetime, str)) or \
                not isinstance(vals.get('date_to'), (datetime, str)):
                continue
            user_tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc
            calendar_tz = pytz.timezone(self.env['resource.calendar'].browse(vals['calendar_id']).tz)
            if user_tz != calendar_tz:
                datetime_from = self._ensure_datetime(vals['date_from'], '%Y-%m-%d %H:%M:%S')
                datetime_to = self._ensure_datetime(vals['date_to'], '%Y-%m-%d %H:%M:%S')
                if datetime_from and datetime_to:
                    vals['date_from'] = self._convert_timezone(datetime_from, user_tz, calendar_tz)
                    vals['date_to'] = self._convert_timezone(datetime_to, user_tz, calendar_tz)
        return vals_list

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = self._prepare_public_holidays_values(vals_list)
        res = super().create(vals_list)
        time_domain_dict = res._get_time_domain_dict()
        self._reevaluate_leaves(time_domain_dict)
        return res

    def write(self, vals):
        time_domain_dict = self._get_time_domain_dict()
        res = super().write(vals)
        time_domain_dict.extend(self._get_time_domain_dict())
        self._reevaluate_leaves(time_domain_dict)

        return res

    def unlink(self):
        time_domain_dict = self._get_time_domain_dict()
        res = super().unlink()
        self._reevaluate_leaves(time_domain_dict)

        return res

class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    associated_leaves_count = fields.Integer("Leave Count", compute='_compute_associated_leaves_count')

    def _compute_associated_leaves_count(self):
        leaves_read_group = self.env['resource.calendar.leaves'].read_group(
            [('resource_id', '=', False)],
            ['calendar_id'],
            ['calendar_id']
        )
        result = dict((data['calendar_id'][0] if data['calendar_id'] else 'global', data['calendar_id_count']) for data in leaves_read_group)
        global_leave_count = result.get('global', 0)
        for calendar in self:
            calendar.associated_leaves_count = result.get(calendar.id, 0) + global_leave_count
