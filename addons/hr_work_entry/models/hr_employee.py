# Part of Odoo. See LICENSE file for full copyright and licensing details.


from collections import defaultdict
from itertools import groupby

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL

from odoo.addons.hr_work_entry.models.utils import (
    date_list_to_ranges,
    remove_days_from_range,
)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    has_work_entries = fields.Boolean(compute='_compute_has_work_entries', groups="base.group_system,hr.group_hr_user")
    work_entry_source = fields.Selection(readonly=False, related="version_id.work_entry_source", inherited=True, groups="base.group_system,hr.group_hr_manager")
    work_entry_source_calendar_invalid = fields.Boolean(related="version_id.work_entry_source_calendar_invalid", inherited=True, groups="hr.group_hr_manager")

    def _compute_has_work_entries(self):
        if self.ids:
            result = dict(self.env.execute_query(SQL(
                """ SELECT id, EXISTS(SELECT 1 FROM hr_work_entry WHERE employee_id = e.id LIMIT 1)
                      FROM hr_employee e
                     WHERE id in %s """,
                tuple(self.ids),
            )))
        else:
            result = {}

        for employee in self:
            employee.has_work_entries = result.get(employee._origin.id, False)

    def create_version(self, values):
        new_version = super().create_version(values)
        new_version.update({
            'date_generated_from': fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
            'date_generated_to': fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
        })
        return new_version

    def action_open_work_entries(self, initial_date=False):
        self.ensure_one()
        ctx = {'default_employee_id': self.id}
        if initial_date:
            ctx['initial_date'] = initial_date
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('%s work entries', self.display_name),
            'view_mode': 'calendar,list,form',
            'res_model': 'hr.work.entry',
            'path': 'work-entries',
            'context': ctx,
            'domain': [('employee_id', '=', self.id)],
        }

    def generate_work_entries(self, date_start, date_stop, force=False):
        date_start = fields.Date.to_date(date_start)
        date_stop = fields.Date.to_date(date_stop)

        if self:
            versions = self._get_versions_with_contract_overlap_with_period(date_start, date_stop)
        else:
            versions = self._get_all_versions_with_contract_overlap_with_period(date_start, date_stop)
        return versions.generate_work_entries(date_start, date_stop, force=force)

    @api.model
    def regenerate_work_entries_from_dates(
        self,
        employee_dates: list[dict],
    ):
        """
        Use this function if you want to regenerate work entries, but you don't
        have the date ranges (i.e.: date_from and date_to), but instead
        individual dates. This function will build the ranges from the given
        dates.
        employee_dates is in the format [{employee_id: 4, date: 1/1/2020}] to
        facilitate batch regeneration for multiple employees at once.
        """
        # will be used as prefetch_ids to reduce number of db queries
        all_employee_ids = []

        # build ranges, and group employees by range
        employee_by_range = defaultdict(list)
        employee_dates.sort(key=lambda ed: ed['employee_id'])
        for employee_id, group in groupby(
            employee_dates,
            lambda ed: ed['employee_id'],
        ):
            dates = [g['date'] for g in group]
            ranges = date_list_to_ranges(dates)
            for range in ranges:
                date_from, date_to = range['start'], range['stop']
                employee_by_range[date_from, date_to].append(employee_id)
            all_employee_ids.append(employee_id)

        for range, employee_ids in employee_by_range.items():
            employee_ids = self.browse(employee_ids).with_prefetch(
                all_employee_ids,
            )
            employee_ids.regenerate_work_entries(range[0], range[1])

    def regenerate_work_entries(self, date_from, date_to):
        """
        Nullifies self's unvalidated work entries between date_from and date_to,
        then generates work entries for all days between date_from and date_to
        that do not have any validated work entries.
        Regenerating a work entry is thus nullifying it, then generating it.
        """
        work_entries = self.env['hr.work.entry'].search(
            Domain.AND(
                [
                    Domain('employee_id', 'in', self.ids),
                    Domain('date', '>=', date_from),
                    Domain('date', '<=', date_to),
                ],
            ),
        )

        # "archiving" all unvalidated work entries in the range
        unvalidated_work_entries = work_entries.filtered_domain(
            Domain('state', '!=', 'validated'),
        )
        fields_to_nullify = self.env[
            'hr.work.entry'
        ]._work_entry_fields_to_nullify()
        unvalidated_work_entries.write(
            {field: False for field in fields_to_nullify},
        )

        # regrouping the data to employees per range will allow us to then
        # efficiently call `generate_work_entries()`
        validated_work_entries = work_entries - unvalidated_work_entries
        validated_we_by_employee = validated_work_entries.grouped('employee_id')
        default_range = {'start': date_from, 'stop': date_to}
        employees_by_range = defaultdict(lambda: self.env['hr.employee'])
        for employee in self:
            # days with validated work entries should not be generated, so we
            # need to remove them from the employee's range
            validated_work_entries = validated_we_by_employee.get(employee, [])
            validated_days = [we.date for we in validated_work_entries]
            ranges = remove_days_from_range(default_range, validated_days)
            # assign the new range to the employee
            for range in ranges:
                date_from, date_to = range['start'], range['stop']
                employees_by_range[date_from, date_to] |= employee

        for range, employees in employees_by_range.items():
            employees.generate_work_entries(range[0], range[1], True)
