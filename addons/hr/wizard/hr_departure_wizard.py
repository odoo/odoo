# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


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
    departure_date = fields.Date(string="Departure Date", required=True, default=_get_default_departure_date)
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
                        'next': next_action
                    }
                }
        self.employee_ids.write({
            'departure_reason_id': self.departure_reason_id,
            'departure_description': self.departure_description,
            'departure_date': self.departure_date,
        })
        archived_users = self.env['res.users']
        allow_archived_users = self.env['res.users']
        unarchived_users = self.env['res.users']
        if self.remove_related_user:
            related_users = self.employee_ids.grouped('user_id')
            related_employees_count = dict(self.env['hr.employee'].sudo()._read_group(
                    domain=[('user_id', 'in', self.employee_ids.user_id.ids)],
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
        for employee in self.employee_ids.filtered(lambda emp: emp.active):
            if self.env.context.get('employee_termination', False):
                employee.with_context(no_wizard=True).action_archive()
                if self.remove_related_user and employee.user_id in allow_archived_users:
                    archived_users |= employee.user_id
                    employee.user_id.sudo().action_archive()

        next_action = {'type': 'ir.actions.act_window_close'}
        if archived_users:
            message = self.env._(
                "The following users have been archived: %s",
                ', '.join(archived_users.mapped('name'))
            )
            next_action = _get_user_archive_notification_action(message, 'success', next_action)
        if unarchived_users:
            message = self.env._(
                "The following users have not been archived: %s",
                ', '.join(unarchived_users.mapped('name'))
            )
            next_action = _get_user_archive_notification_action(message, 'danger', next_action)

        return next_action
