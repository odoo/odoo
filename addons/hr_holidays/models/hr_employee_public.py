# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    leave_manager_id = fields.Many2one(
        'res.users', string='Time Off Approver',
        compute='_compute_leave_manager', store=True, readonly=False,
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
        help='Select the user responsible for approving "Time Off" of this employee.\n'
             'If empty, the approval is done by an Administrator or Approver (determined in settings/users).')
    leave_date_to = fields.Date('To Date', compute='_compute_leave_status')
    show_leaves = fields.Boolean('Able to see Remaining Time Off', compute='_compute_show_leaves')
    is_absent = fields.Boolean('Absent Today', compute='_compute_leave_status', search='_search_absent_employee')
    hr_icon_display = fields.Selection(selection_add=[
        ('presence_holiday_absent', 'On leave'),
        ('presence_holiday_present', 'Present but on leave')])
    allocation_display = fields.Char(compute='_compute_allocation_display')
    allocation_remaining_display = fields.Char(related='employee_id.allocation_remaining_display')

    def _compute_show_leaves(self):
        self._compute_from_employee('show_leaves')

    def _compute_leave_manager(self):
        self._compute_from_employee('leave_manager_id')

    def _compute_leave_status(self):
        self._compute_from_employee(['leave_date_to', 'is_absent'])

    def _search_absent_employee(self, operator, value):
        if operator != 'in':
            return NotImplemented
        # This search is only used for the 'Absent Today' filter however
        # this only returns employees that are absent right now.
        today_start = date.today()
        today_end = today_start + timedelta(1)
        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', '!=', False),
            ('state', '=', 'validate'),
            ('date_from', '<', today_end),
            ('date_to', '>=', today_start),
        ])
        return [('id', 'in', holidays.employee_id.ids)]

    def _compute_allocation_display(self):
        self._compute_from_employee('allocation_display')

    def action_time_off_dashboard(self):
        self.ensure_one()
        if self.is_user:
            return self.employee_id.action_time_off_dashboard()
