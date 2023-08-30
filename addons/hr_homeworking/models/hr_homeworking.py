# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from datetime import timedelta
from odoo.addons.resource.models.utils import string_to_datetime, datetime_to_string
from odoo.exceptions import ValidationError
from dateutil.rrule import rrule, DAILY

DAYS = ['monday_location_id', 'tuesday_location_id', 'wednesday_location_id', 'thursday_location_id', 'friday_location_id', 'saturday_location_id', 'sunday_location_id']
DAYS_STRING = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']


class HrEmployeeLocation(models.Model):
    _name = "hr.employee.location"
    _description = "Employee Location"

    work_location_id = fields.Many2one('hr.work.location', required=True, string="Location")
    work_location_name = fields.Char(related='work_location_id.name', string="Location name")
    work_location_type = fields.Selection(related="work_location_id.location_type")
    employee_id = fields.Many2one('hr.employee', default=lambda self: self.env.user.employee_id, required=True, ondelete="cascade")
    employee_name = fields.Char(related="employee_id.name")
    weekday = fields.Integer(compute="_compute_weekday", store=True)
    weekly = fields.Boolean(default=False)
    start_date = fields.Date(string="Start Date")
    today_next_date = fields.Date(compute="_compute_today_next_date")
    day_week_string = fields.Char(compute="_compute_day_week_string")
    end_date_create = fields.Date(help="used in computations on employee location pop-up in calendar view.")
    removed = fields.Boolean(default=False, help="User removed worklocation on one day that has a weekly location")
    parent_default_homeworking_id = fields.Many2one("hr.employee.location", help="original weekly worklocation on a removed worklocation", ondelete="cascade")
    child_removed_ids = fields.One2many("hr.employee.location", 'parent_default_homeworking_id')
    current_location = fields.Boolean(default=True, help="Whether the record is the most recent weekly worklocation")
    end_date = fields.Date(help="end date of a previous weekly worklocation (as opposed to current worklocation)")

    _sql_constraints = [
        ('uniq_exceptional_per_day', 'unique(employee_id, weekly, start_date, current_location)', 'Only one default work location and one exceptional work location per day per employee.'),
    ]

    @api.constrains("employee_id", "weekday", "current_location")
    def _check_current(self):
        for record in self:
            if record.current_location:
                if self.search_count([('employee_id', '=', record.employee_id.id), ('weekday', '=', record.weekday), ('current_location', '=', True)]) > 1:
                    raise ValidationError(_('Only one current default work location per day per employee. can have some previous default work location'))

    @api.depends('start_date', 'weekly')
    def _compute_weekday(self):
        for record in self:
            if not record.weekly:
                continue
            if record.start_date:
                record.weekday = record.start_date.weekday()

    @api.depends('start_date', 'end_date_create')
    def _compute_today_next_date(self):
        today = fields.Date().today()
        for record in self:
            if record.start_date < today:
                if record.end_date_create >= today:
                    record.today_next_date = today
                else:
                    if record.start_date.weekday() <= today.weekday() and today.weekday() <= record.end_date_create.weekday():
                        record.today_next_date = today
                    else:
                        offset = (record.start_date.weekday() - fields.Date.today().weekday() + 7) % 7
                        record.today_next_date = today + timedelta(days=offset)
            else:
                record.today_next_date = record.start_date

    @api.depends('start_date', 'end_date_create', 'weekly')
    def _compute_day_week_string(self):
        for record in self:
            if record.weekly and record.end_date_create - record.start_date > timedelta(days=7):
                raise ValidationError(_('A weekly location cannot have a duration of more than 7 days'))
            if (record.start_date > record.end_date_create):
                record.end_date_create = record.start_date
            weekdays_name = ""
            if record.start_date.weekday() > record.end_date_create.weekday():
                for i in range(0, record.end_date_create.weekday()):
                    weekdays_name = weekdays_name + ", " + DAYS_STRING[i]
                for i in range(record.start_date.weekday(), 7):
                    weekdays_name = weekdays_name + ", " + DAYS_STRING[i]
            else:
                for i in range(record.start_date.weekday(), record.end_date_create.weekday() + 1):
                    weekdays_name = weekdays_name + ", " + DAYS_STRING[i]
            record.day_week_string = weekdays_name

    def _save_previous_default_worklocation(self):
        self.ensure_one()
        if self.start_date >= fields.Date().today():
            self.unlink()
        else:
            self.current_location = False
            self.end_date = fields.Date().today() - timedelta(days=1)
            self.child_removed_ids.filtered(lambda child: child.start_date >= fields.Date.today()).unlink()
            return False

    def _next_weekday_date_after_today(self, date):
        today = fields.Date().today()
        offset = (date.weekday() - fields.Date.today().weekday() + 7) % 7
        return today + timedelta(days=offset)

    def _removed_worklocation_to_active_worklocation(self, work_location_id):
        self.update({
            "removed": False,
            "parent_default_homeworking_id": False,
            "work_location_id": work_location_id,
        })

    def _check_exceptional_work_location(self, vals):
        date = vals.get("start_date", self.start_date)
        work = vals.get("work_location_id", self.work_location_id.id)
        employee_id = vals.get("employee_id", self.employee_id.id)
        exception_work_location = self.env['hr.employee.location'].search([
            ('start_date', '=', date),
            ('employee_id.id', '=', employee_id),
            ('weekly', '=', False),
            ('id', '!=', self.id),
        ])
        return exception_work_location, date, work, employee_id

    def add_exceptional_worklocation(self, vals):
        exceptional, date, work, employee_id = self._check_exceptional_work_location(vals)
        if exceptional:
            exceptional.unlink()
        self.env['hr.employee.location'].create({
            'work_location_id': work,
            'employee_id': employee_id,
            'start_date': date,
        })
        return True

    def exceptional_worklocation_to_default_worklocation(self, vals, unlink=True):
        default_date = vals.get("start_date")
        if default_date:
            default_date = string_to_datetime(default_date).date()
        else:
            default_date = self.start_date
        date = default_date
        default_work = self.env['hr.employee.location'].search([
            ("employee_id.id", "=", self.employee_id.id),
            ("weekday", "=", default_date.weekday()),
            ("weekly", "=", True),
            ("current_location", "=", True)
        ])
        self.env['hr.employee.location'].search([
            ("employee_id.id", "=", self.employee_id.id),
            ("start_date", "=", date),
            ("removed", "=", True),
        ]).unlink()
        if default_date < fields.Date().today():
            default_date = self._next_weekday_date_after_today(date)
        if default_work:
            default_work._save_previous_default_worklocation()
        if date != default_date:
            self.env['hr.employee.location'].create({
                'employee_id': self.employee_id.id,
                'start_date': default_date,
                'work_location_id': vals.get("work_location_id", self.work_location_id.id),
                'weekly': True
            })
            vals["weekly"] = False
        if unlink:
            self.unlink()
        else:
            if vals.get("work_location_id"):
                self.work_location_id = vals["work_location_id"]
        return vals

    def add_removed_work_location(self, date):
        self.ensure_one()
        self.env['hr.employee.location'].create({
            'work_location_id': self.work_location_id.id,
            'employee_id': self.employee_id.id,
            'start_date': date,
            'removed': True,
            'parent_default_homeworking_id': self.id,
        })

    def delete_default_worklocation(self):
        self.ensure_one()
        self.employee_id.with_context(no_loop=True).write({DAYS[self.weekday]: False})
        self._save_previous_default_worklocation()

    def _get_new_worklocation_vals(self, vals):
        date = vals.get("start_date")
        except_vals = {
            "start_date": date,
            "work_location_id": vals.get("work_location_id", self.work_location_id.id),
            "weekly": vals.get("weekly", self.weekly),
            "employee_id": vals.get("employee_id", self.employee_id.id),
        }
        # to not rewrite the past
        self._save_previous_default_worklocation()
        values = vals
        employeeLocation = self.env['hr.employee.location']
        if date < fields.Date().today():
            employeeLocation.add_exceptional_worklocation(except_vals)
            values["start_date"] = employeeLocation._next_weekday_date_after_today(date)
        return values

    # create a default worklocation with values in vals and manages the link between the different records
    def create_default_worklocation(self, vals, from_create=False, unlink=True):
        date = vals.get("start_date", self.start_date)
        employee_id = vals.get("employee_id", self.employee_id.id)
        work_location_id = vals.get("work_location_id", self.work_location_id.id)
        default_work_location = self.env['hr.employee.location'].search([
            ("employee_id.id", "=", employee_id),
            ("weekly", "=", True),
            ("weekday", "=", date.weekday()),
            ("current_location", "=", True),
            ("id", "!=", self.id)
        ])
        if default_work_location:
            val = default_work_location._get_new_worklocation_vals({
                "start_date": date,
                "employee_id": employee_id,
                "work_location_id": work_location_id
            })
            vals["start_date"] = val.get("start_date", date)
            if from_create:
                return vals
            else:
                values = {
                    "start_date": val.get("start_date", date),
                    "employee_id": employee_id,
                    "work_location_id": work_location_id,
                    "weekly": True,
                }
                return super().create(values)
        else:
            exceptions, dummy, dummy, dummy = self._check_exceptional_work_location(vals)
            if exceptions.filtered(lambda excep: excep.id != self.id):
                exceptions.unlink()
            if date < fields.Date().today():
                new_values = {
                    'start_date': date,
                    'employee_id': employee_id,
                    'work_location_id': work_location_id,
                }
                if from_create or (exceptions and exceptions.filtered(lambda excep: excep.id != self.id)):
                    super().create(new_values)
                else:
                    super().write(new_values)
                vals["start_date"] = self._next_weekday_date_after_today(date)
            if from_create:
                return vals
            else:
                vals.update({
                    "work_location_id": work_location_id,
                    "weekly": True,
                    "start_date": date,
                    "employee_id": employee_id,
                })
                return super().create(vals)

    # clean values in vals_list to manage the link between record
    def _clean_values_to_create(self, vals_list):
        clean_vals_list = []
        for vals in vals_list:
            date = string_to_datetime(vals.get("start_date")).date()
            employee_id = vals.get("employee_id") or self.env.context.get('default_employee_id') or self.env.user.employee_id.id
            if vals.get("weekly"):
                clean_vals_list.append(self.create_default_worklocation({
                    'start_date': date,
                    'employee_id': employee_id,
                    'work_location_id': vals["work_location_id"],
                    'weekly': True
                }, from_create=True))
            else:
                exceptions_worklocation = self.env['hr.employee.location'].search([
                    ("employee_id.id", "=", employee_id),
                    ("weekly", "=", False),
                    ("start_date", "=", date),
                ])
                worklocation_exception = exceptions_worklocation.filtered(lambda a: not a.removed)
                if worklocation_exception:
                    worklocation_exception.work_location_id = vals.get("work_location_id")
                else:
                    removed_worklocation_exception = exceptions_worklocation.filtered(lambda a: a.removed)
                    if removed_worklocation_exception:
                        removed_worklocation_exception._removed_worklocation_to_active_worklocation(vals.get("work_location_id"))
                    else:
                        clean_vals_list.append(vals)
        return clean_vals_list

    @api.model_create_multi
    def create(self, vals_list):
        extended_vals_list = []
        for vals in vals_list:
            if vals.get("end_date_create"):
                start_date = string_to_datetime(vals.get("start_date")).date()
                end_date = string_to_datetime(vals.get("end_date_create")).date()
                days_list = list(rrule(DAILY, start_date, until=end_date))
                vals.pop("end_date_create")
                for day in days_list:
                    extended_vals_list.append({**vals, **{"start_date": datetime_to_string(day)}})
            else:
                extended_vals_list.append(vals)
        res = super().create(self._clean_values_to_create(extended_vals_list))
        for wl in res:
            if wl.weekly:
                wl.employee_id.sudo().with_context(no_loop=True).write({DAYS[wl.weekday]: wl.work_location_id})
        if len(vals_list) == 1 and len(extended_vals_list) != 1:
            return res[0]
        return res
