# -*- coding: utf-8 -*-
from datetime import timedelta, datetime, date

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EmployeeShift(models.Model):
    _name = "employee.shift"
    _description = "Employee Shift"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Shift Name", required=True)
    start_datetime = fields.Datetime(string="Start", required=True)
    end_datetime = fields.Datetime(string="End", required=True)
    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Employees",
        relation="employee_shift_rel",
        column1="shift_id",
        column2="employee_id",
    )

    color = fields.Integer(string="Color")

    display_name = fields.Char(string="Calendar Title", compute="_compute_display_name")

    @api.depends('name', 'employee_ids')
    def _compute_display_name(self):
        for rec in self:
            if rec.employee_ids:
                employees = ", ".join(rec.employee_ids.mapped('name'))
                rec.display_name = "%s - %s" % (rec.name, employees)
            else:
                rec.display_name = rec.name

    @api.constrains('start_datetime', 'end_datetime')
    def _check_dates(self):
        for rec in self:
            if rec.end_datetime and rec.start_datetime:
                if rec.end_datetime <= rec.start_datetime:
                    raise ValidationError("End datetime must be after start datetime.")

    def name_get(self):
        result = []
        for rec in self:
            if rec.employee_ids:
                employees = ", ".join(rec.employee_ids.mapped('name'))
                result.append((rec.id, "%s - %s" % (rec.name, employees)))
            else:
                result.append((rec.id, rec.name))
        return result

    @staticmethod
    def _hex_to_int_color(value):
        """Map a hex color or numeric input to a small integer color index (0-10).
        This maps arbitrary hex values into the calendar's limited color palette.
        """
        # If a hex color like '#ff0000' is provided, hash it into 0..10
        if isinstance(value, str) and value.startswith('#'):
            try:
                return int(value.lstrip('#'), 16) % 11
            except Exception:
                return 0
        try:
            return int(value) % 11
        except Exception:
            return 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'color' in vals:
                vals['color'] = self._hex_to_int_color(vals.get('color'))
        return super(EmployeeShift, self).create(vals_list)

    def write(self, vals):
        if 'color' in vals:
            vals['color'] = self._hex_to_int_color(vals.get('color'))
        return super(EmployeeShift, self).write(vals)

    def create_for_week(self):
        """Duplicate this shift for the next 6 days to cover a full week."""
        for rec in self:
            if not rec.start_datetime or not rec.end_datetime:
                continue
            start_dt = fields.Datetime.to_datetime(rec.start_datetime)
            end_dt = fields.Datetime.to_datetime(rec.end_datetime)
            for i in range(1, 7):
                vals = {
                    'name': rec.name,
                    'start_datetime': fields.Datetime.to_string(start_dt + timedelta(days=i)),
                    'end_datetime': fields.Datetime.to_string(end_dt + timedelta(days=i)),
                    'employee_ids': [(6, 0, rec.employee_ids.ids)],
                    'color': rec.color,
                }
                # create expects a list when using model_create_multi; use env create
                self.env['employee.shift'].create([vals])
        return True

    def action_open_week_wizard(self):
        self.ensure_one()
        return {
            'name': 'Create Shifts for Range',
            'type': 'ir.actions.act_window',
            'res_model': 'shift.week.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_shift_id': self.id, 'default_start_date': False, 'default_end_date': False},
        }


# Wizard transient model for creating shifts in a date range
class ShiftWeekWizard(models.TransientModel):
    _name = 'shift.week.wizard'
    _description = 'Create Shifts for Date Range'

    shift_id = fields.Many2one('employee.shift', string='Shift', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    def apply_create(self):
        self.ensure_one()
        if self.end_date < self.start_date:
            raise models.ValidationError('End Date must be on or after Start Date')
        shift = self.shift_id
        # extract time components from original shift datetimes
        orig_start = fields.Datetime.to_datetime(shift.start_datetime)
        orig_end = fields.Datetime.to_datetime(shift.end_datetime)
        for n in range((self.end_date - self.start_date).days + 1):
            cur_date = self.start_date + timedelta(days=n)
            new_start_dt = datetime.combine(cur_date, orig_start.time())
            new_end_dt = datetime.combine(cur_date, orig_end.time())
            vals = {
                'name': shift.name,
                'start_datetime': fields.Datetime.to_string(new_start_dt),
                'end_datetime': fields.Datetime.to_string(new_end_dt),
                'employee_ids': [(6, 0, shift.employee_ids.ids)],
                'color': shift.color,
            }
            self.env['employee.shift'].create(vals)
        return {'type': 'ir.actions.act_window_close'}
