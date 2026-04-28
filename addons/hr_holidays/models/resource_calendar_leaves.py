# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC, datetime

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    holiday_id = fields.Many2one("hr.leave", string='Time Off Request')
    elligible_for_accrual_rate = fields.Boolean(string='Eligible for Accrual Rate', default=False,
        help="If checked, this time type will be taken into account for accruals computation.")

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
                    existing_leaves = existing_leaves.filtered(
                        lambda leave: not leave.calendar_id or leave.calendar_id == record.calendar_id)
                if existing_leaves:
                    raise ValidationError(self.env._('Two public holidays cannot overlap each other for the same working hours.'))

    def _get_domain(self, time_domain_dict):
        return Domain.OR(
            [
                ('employee_company_id', '=', date['company_id']),
                ('date_to', '>', date['date_from']),
                ('date_from', '<', date['date_to']),
            ]
            for date in time_domain_dict
        ) & Domain('state', 'not in', ['refuse', 'cancel'])

    def _get_time_domain_dict(self):
        return [{
            'company_id': record.company_id.id,
            'date_from': record.date_from,
            'date_to': record.date_to,
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
        self.env.add_to_compute(self.env['hr.leave']._fields['number_of_days'], leaves)
        leaves.sudo().write({
            'state': 'confirm',
        })
        sick_time_status = self.env['hr.work.entry.type'].search([('code', '=', 'LEAVE110')])
        leaves_to_recreate = self.env['hr.leave']
        for previous_duration, leave, state in zip(previous_durations, leaves, previous_states):
            duration_difference = previous_duration - leave.number_of_days
            message = False
            if duration_difference > 0 and leave.work_entry_type_id.requires_allocation:
                message = self.env._(
                    "Due to a change in global time offs, you have been granted %s day(s) back.",
                    duration_difference)
            if leave.number_of_days > previous_duration\
                    and (not sick_time_status or leave.work_entry_type_id not in sick_time_status):
                message = self.env._(
                    "Due to a change in global time offs, %s extra day(s) have been taken from your allocation. Please review this leave if you need it to be changed.",
                    (-1 * duration_difference))
            try:
                leave.sudo().write({'state': state})  # sudo in order to skip _check_approval_update
                leave._check_validity()
                if leave.state == 'validate':
                    # recreate the resource leave that were removed by writing state to draft
                    leaves_to_recreate |= leave
            except ValidationError:
                leave.action_refuse()
                message = self.env._(
                    "Due to a change in global time offs, this leave no longer has the required amount of available allocation and has been set to refused. Please review this leave.")
            if message:
                leave._notify_change(message)
        leaves_to_recreate.sudo()._create_resource_leave()

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
        aware_datetime_to = naive_datetime_from.replace(tzinfo=tz_to)
        return aware_datetime_to.astimezone(UTC).replace(tzinfo=None)

    def _ensure_datetime(self, datetime_representation, date_format=None):
        """
            Be sure to get a datetime object if we have the necessary information.
            :param datetime_reprentation: object which should represent a datetime
            :rtype: datetime if a correct datetime_represtion, None otherwise
        """
        if isinstance(datetime_representation, datetime):
            return datetime_representation
        if isinstance(datetime_representation, str) and date_format:
            return datetime.strptime(datetime_representation, date_format)
        return None

    @api.model_create_multi
    def create(self, vals_list):
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

    @api.depends('calendar_id')
    def _compute_company_id(self):
        for leave in self:
            leave.company_id = leave.holiday_id.employee_id.company_id or leave.calendar_id.company_id or self.env.company
