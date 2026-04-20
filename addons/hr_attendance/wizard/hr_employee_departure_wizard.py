from odoo import api, fields, models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    has_ongoing_attendance = fields.Boolean(
        string='Has Ongoing Attendance',
        compute='_compute_attendance_info'
    )
    has_multiple_attendances = fields.Boolean(
        string='Has Multiple Ongoing Attendances',
        compute='_compute_attendance_info'
    )
    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Ongoing Attendance',
        compute='_compute_attendance_id',
        store=True,
        readonly=False
    )
    attendance_check_in = fields.Datetime(
        string='Check In',
        related='attendance_id.check_in',
        readonly=True
    )
    attendance_worked_hours = fields.Float(
        string='Hours Since Check-in',
        compute='_compute_worked_hours',
        digits=(16, 2)
    )
    attendance_action = fields.Selection([
        ('checkout', 'Check out now'),
        ('delete', 'Delete attendance'),
    ], string='Action', default='checkout')

    @api.depends('employee_id')
    def _compute_attendance_info(self):
        for wizard in self:
            if wizard.employee_id:
                attendances = self.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', wizard.employee_id.id),
                    ('check_out', '=', False),
                ])

                wizard.has_ongoing_attendance = len(attendances) > 0
                wizard.has_multiple_attendances = len(attendances) > 1
            else:
                wizard.has_ongoing_attendance = False
                wizard.has_multiple_attendances = False

    @api.depends('employee_id')
    def _compute_attendance_id(self):
        for wizard in self:
            if wizard.employee_id:
                attendances = self.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', wizard.employee_id.id),
                    ('check_out', '=', False),
                ])
                wizard.attendance_id = attendances[0] if len(attendances) == 1 else False
            else:
                wizard.attendance_id = False

    @api.depends('attendance_id', 'attendance_id.check_in')
    def _compute_worked_hours(self):
        for wizard in self:
            if wizard.attendance_id and wizard.attendance_id.check_in:
                delta = fields.Datetime.now() - wizard.attendance_id.check_in
                wizard.attendance_worked_hours = delta.total_seconds() / 3600
            else:
                wizard.attendance_worked_hours = 0.0

    def action_register_departure(self):
        if self.attendance_id and self.attendance_action:
            if self.attendance_action == 'checkout':
                self.attendance_id.sudo().write({
                    'check_out': fields.Datetime.now(),
                })
            elif self.attendance_action == 'delete':
                self.attendance_id.sudo().unlink()

        return super().action_register_departure()
