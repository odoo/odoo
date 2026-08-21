from odoo import api, fields, models, Command
from odoo.fields import Domain
from odoo.exceptions import ValidationError


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    version_ids = fields.One2many('hr.version', 'resource_calendar_id', readonly=True, copy=False)
    employees_count = fields.Integer("Employees count", compute='_compute_employees_count')
    is_duplicate_calendar = fields.Boolean(compute='_compute_is_duplicate_calendar')

    @api.constrains('company_id')
    def _check_company_id(self):
        for res_calendar in self:
            if res_calendar.company_id:
                if any(res_calendar.company_id not in version.company_id.parent_ids for version in res_calendar.version_ids):
                    raise ValidationError(self.env._("The working schedule '%s' is linked to version(s) not compatible with its new company.") % res_calendar.name)

    @api.model
    def create_calendar_copy_with_updates(self, calendar_id, vals):
        """
        Create a copy of the calendar, Parse the provided changes (vals)
        Then apply the modifications to the copied calendar, ensuring that
        `attendance_ids` are correctly remapped to the new calendar's attendance records.
        """
        calendar = self.browse(calendar_id).exists()
        if not calendar:
            return False

        copy_defaults = {'name': self.env._("%s (copy)", calendar.name)}
        if 'company_id' in vals:
            copy_defaults['company_id'] = vals.get('company_id')
        if 'calendar_type' in vals:
            copy_defaults['calendar_type'] = vals.get('calendar_type')

        new_calendar = calendar.copy(copy_defaults)

        attendance_changes = vals.get('attendance_ids', [])
        if attendance_changes:
            def _get_line_key(line):
                recurrency_excluded_occurences_tuple = line.recurrency_excluded_occurences
                return (
                    line.dayofweek,
                    line.day_period,
                    line.hour_from,
                    line.hour_to,
                    line.date,
                    line.recurrency,
                    tuple(sorted(recurrency_excluded_occurences_tuple)) if isinstance(recurrency_excluded_occurences_tuple, list) else recurrency_excluded_occurences_tuple,
                    line.recurrency_type,
                    line.recurrency_interval,
                    line.recurrency_end_type,
                    line.recurrency_count,
                )

            commands = []
            line_map = {_get_line_key(line): line for line in new_calendar.attendance_ids}
            for command in attendance_changes:
                if len(command) >= 3:
                    cmd_type = command[0]
                    old_line_id = command[1]
                    line_vals = command[2]

                    if cmd_type == 0:
                        commands.append(Command.create(line_vals))

                    elif cmd_type == 1:
                        old_line = self.env['resource.calendar.attendance'].browse(old_line_id)
                        if old_line and (matched_line := line_map.get(_get_line_key(old_line))):
                            commands.append(Command.update(matched_line.id, line_vals))

                    elif cmd_type == 2:
                        old_line = self.env['resource.calendar.attendance'].browse(old_line_id)
                        if old_line and (matched_line := line_map.get(_get_line_key(old_line))):
                            commands.append(Command.delete(matched_line.id))

            vals['attendance_ids'] = commands

        if vals:
            new_calendar.write(vals)
        return new_calendar.id

    def transfer_leaves_to(self, other_calendar, resources=None, from_date=None):
        """
            Transfer some resource.calendar.leaves from 'self' to another calendar 'other_calendar'.
            Transfered leaves linked to `resources` (or all if `resources` is None) and starting
            after 'from_date' (or today if None).
        """
        from_date = from_date or fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        domain = [
            ('calendar_id', 'in', self.ids),
            ('date_from', '>=', from_date),
        ]
        domain = Domain.AND([domain, [('resource_id', 'in', resources.ids)]]) if resources else domain

        self.env['resource.calendar.leaves'].search(domain).write({
            'calendar_id': other_calendar.id,
        })

    def _compute_employees_count(self):
        employees_per_calendar = dict(self.env['hr.employee']._read_group(
            domain=[
                ('company_id', 'in', self.mapped('company_id').ids),
                ('resource_calendar_id', 'in', self.ids)
            ],
            groupby=['resource_calendar_id'],
            aggregates=['__count']))
        for calendar in self:
            calendar.employees_count = employees_per_calendar.get(calendar, 0)

    @api.depends('company_id', 'calendar_type', 'attendance_ids')
    def _compute_is_duplicate_calendar(self):
        valid_calendars = self.filtered(lambda c: c.attendance_ids)
        if not valid_calendars:
            return

        (self - valid_calendars).is_duplicate_calendar = False

        similar_calendars = self._get_similar_calendars(valid_calendars)

        for calendar in valid_calendars:
            key = (
                calendar.company_id,
                calendar.calendar_type,
                calendar.hours_per_week,
                calendar.hours_per_day,
            )
            candidate_calendars = similar_calendars.get(key, self.env['resource.calendar']) - calendar

            if not candidate_calendars:
                calendar.is_duplicate_calendar = False
                continue

            calendar.is_duplicate_calendar = any(
                candidate._get_attendance_signature() == calendar._get_attendance_signature()
                for candidate in candidate_calendars
            )

    def _get_similar_calendars(self, calendars):
        search_domain = [
            ('active', '=', True),
            ('company_id', 'in', calendars.company_id.ids),
            ('calendar_type', 'in', calendars.mapped('calendar_type')),
            ('hours_per_week', 'in', calendars.mapped('hours_per_week')),
            ('hours_per_day', 'in', calendars.mapped('hours_per_day')),
        ]

        calendar_read_group = self.env['resource.calendar']._read_group(
            search_domain,
            ['company_id', 'calendar_type', 'hours_per_week', 'hours_per_day'],
            ['id:recordset'],
        )

        return {
            (company, calendar_type, hours_week, hours_day): records
            for company, calendar_type, hours_week, hours_day, records in calendar_read_group
        }

    def _get_attendance_signature(self):
        self.ensure_one()
        return frozenset(
            (
                att.dayofweek,
                att.day_period,
                att.hour_from,
                att.hour_to,
                att.date,
                att.recurrency,
                tuple(sorted(att.recurrency_excluded_occurences)) if isinstance(att.recurrency_excluded_occurences, list) else att.recurrency_excluded_occurences,
                att.recurrency_type,
                att.recurrency_interval,
                att.recurrency_end_type,
                att.recurrency_count,
            )
            for att in self.attendance_ids
        )

    def action_view_duplicate_working_schedules(self):
        self.ensure_one()

        similar_calendars = self._get_similar_calendars(self)
        key = (
            self.company_id,
            self.calendar_type,
            self.hours_per_week,
            self.hours_per_day,
        )
        candidate_calendars = similar_calendars.get(key, self.env['resource.calendar']) - self

        duplicate_ids = [
            candidate.id for candidate in candidate_calendars
            if candidate._get_attendance_signature() == self._get_attendance_signature()
        ]

        return {
            'name': self.env._('Duplicate Working Schedules'),
            'type': 'ir.actions.act_window',
            'res_model': 'resource.calendar',
            'view_mode': 'list,form',
            'domain': [('id', 'in', duplicate_ids)],
            'target': 'current',
        }
