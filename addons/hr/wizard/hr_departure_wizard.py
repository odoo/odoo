# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


class HrDepartureWizard(models.TransientModel):
    _name = 'hr.departure.wizard'
    _description = 'Departure Wizard'

    def _get_default_departure_date(self):
        if len(active_ids := self.env.context.get('active_ids', [])) == 1:
            employee = self.env['hr.employee'].browse(active_ids[0])
            departure_date = employee and employee._get_departure_date()
        else:
            departure_date = False

        return departure_date or fields.Date.today()

    def _get_default_employee_ids(self):
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            return self.env['hr.employee'].browse(active_ids).filtered(lambda e: e.company_id in self.env.companies)
        return self.env['hr.employee']

    def _get_domain_employee_ids(self):
        return [('active', '=', True), ('company_id', 'in', self.env.companies.ids)]

    departure_reason_id = fields.Many2one("hr.departure.reason", required=True,
        default=lambda self: self.env['hr.departure.reason'].search([], limit=1),
    )
    departure_description = fields.Html(string="Additional Information")
    departure_date = fields.Date(string="Contract End Date", required=True, default=_get_default_departure_date)
    employee_ids = fields.Many2many(
        'hr.employee', string='Employees', required=True,
        default=_get_default_employee_ids,
        context={'active_test': False},
        domain=_get_domain_employee_ids,
    )

    is_user_employee = fields.Boolean(
        string="User Employee",
        compute='_compute_is_user_employee',
    )
    remove_related_user = fields.Boolean(
        string="Related User",
        help="If checked, the related user will be removed from the system.",
    )

    set_date_end = fields.Boolean(string="Set Contract End Date", default=lambda self: self.env.user.has_group('hr.group_hr_user'),
        help="Set the end date on the current contract.")

    @api.depends('employee_ids.user_id')
    def _compute_is_user_employee(self):
        for wizard in self:
            # Check if at least one employee in the wizard has a user and all the employees related to this user are in the wizard
            # This is to ensure that the user is not removed if there are other employees related to it
            related_users = wizard.employee_ids.user_id
            wizard.is_user_employee = bool(related_users)

    def action_register_departure(self):
        def _get_user_archive_notification_action(message, message_type, next_action):
            return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': self.env._("User Archive Notification"),
                        'type': message_type,
                        'message': message,
                        'next': next_action,
                    },
                }

        employee_ids = self.employee_ids
        active_versions = employee_ids.version_id

        if any(v.contract_date_start and v.contract_date_start > self.departure_date for v in active_versions):
            raise UserError(self.env._("Departure date can't be earlier than the start date of current contract."))

        allow_archived_users = self.env['res.users']
        unarchived_users = self.env['res.users']
        if self.remove_related_user:
            related_users = employee_ids.grouped('user_id')
            related_employees_count = dict(self.env['hr.employee'].sudo()._read_group(
                    domain=[('user_id', 'in', employee_ids.user_id.ids)],
                    groupby=['user_id'],
                    aggregates=['id:count'],
                ))
            for user, emps in related_users.items():
                if not user:
                    continue
                if len(emps) == related_employees_count.get(user, 0):
                    allow_archived_users |= user
                else:
                    unarchived_users |= user

        archived_employees = self.env['hr.employee']
        archived_users = self.env['res.users']
        for employee in employee_ids.filtered(lambda emp: emp.active):
            if self.env.context.get('employee_termination', False):
                archived_employees |= employee
                if self.remove_related_user and employee.user_id in allow_archived_users:
                    archived_users |= employee.user_id

        archived_employees.with_context(no_wizard=True).action_archive()
        archived_users.action_archive()

        employee_ids.write({
            'departure_reason_id': self.departure_reason_id,
            'departure_description': self.departure_description,
            'departure_date': self.departure_date,
        })

        if self.set_date_end:
            # Write date and update state of current contracts
            active_versions = active_versions.filtered(lambda v: v.contract_date_start)
            active_versions.write({'contract_date_end': self.departure_date})

        next_action = {'type': 'ir.actions.act_window_close'}
        if archived_users:
            message = self.env._(
                "The following users have been archived: %s",
                ', '.join(archived_users.mapped('name'))
            )
            next_action = _get_user_archive_notification_action(message, 'success', next_action)
        if unarchived_users:
            message = self.env._(
                "The following users have not been archived as they are still linked to another active employees: %s",
                ', '.join(unarchived_users.mapped('name'))
            )
            next_action = _get_user_archive_notification_action(message, 'danger', next_action)

        return next_action
