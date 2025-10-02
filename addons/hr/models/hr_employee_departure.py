# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployeeDeparture(models.Model):
    _name = "hr.employee.departure"
    _description = "Employee Departure"

    def _get_default_departure_date(self):
        employee = self.env['hr.employee'].browse(self.env.context.get('active_id', False))
        departure_date = employee._get_departure_date() if employee else False
        return departure_date or fields.Date.today()

    def _get_default_employee_id(self):
        active_id = self.env.context.get('active_id', [])
        if active_id:
            return self.env['hr.employee'].browse(active_id)
        return self.env['hr.employee']

    def _get_domain_employee_id(self):
        return [('active', '=', True), ('company_id', 'in', self.env.companies.ids)]

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        default=_get_default_employee_id,
        domain=lambda self: self._get_domain_employee_id(),
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')], default="draft", required=True)
    country_code = fields.Char(compute="_compute_country_code")
    departure_reason_id = fields.Many2one(
        "hr.departure.reason",
        string="End Reason",
        default=lambda self: self.env['hr.departure.reason'].search([], limit=1),
        required=True, ondelete='restrict')
    departure_description = fields.Html(string="Additional Information")
    departure_date = fields.Date(
        string="Departure Date",
        default=_get_default_departure_date,
        required=True)
    action_at = fields.Selection([
        ('departure_date', 'Departure Date'),
        ('other', 'Other Date'),
    ], default='departure_date', required=True)
    action_other_date = fields.Date()
    is_user_employee = fields.Boolean(
        compute='_compute_is_user_employee',
        export_string_translation=False,
    )
    do_archive_user = fields.Boolean(
        string="Archive Related User",
        help="If checked, the related user will be removed from the system.",
    )
    do_archive_employee = fields.Boolean(default=True, string="Archive Employee")
    do_set_date_end = fields.Boolean(
        string="Set Contract End Date",
        default=lambda self: self.env.user.has_group('hr_contract.group_hr_contract_manager'),
        help="Limit contracts date to End of Contract and cancel future ones.")
    has_selected_actions = fields.Boolean(compute='_compute_has_selected_actions')
    apply_immediately = fields.Boolean(compute="_compute_apply_immediately")
    apply_date = fields.Date(compute='_compute_apply_date', store=True)

    def _get_action_fields(self):
        return [f for f in self._fields if f.startswith('do_')]

    @api.depends('employee_id')
    def _compute_country_code(self):
        for departure in self:
            departure.country_code = departure.employee_id.company_id.country_id.code

    @api.depends('employee_id.user_id')
    def _compute_is_user_employee(self):
        for wizard in self:
            wizard.is_user_employee = bool(wizard.employee_id.user_id)

    @api.depends(lambda self: self._get_action_fields())
    def _compute_has_selected_actions(self):
        action_fields = self._get_action_fields()
        for departure in self:
            departure.has_selected_actions = any(departure[field] for field in action_fields)

    @api.depends('action_at', 'departure_date', 'action_other_date')
    def _compute_apply_immediately(self):
        today = fields.Date.today()
        for departure in self:
            if departure.state in ['done', 'cancel']:
                departure.apply_immediately = False
            elif departure.action_at == "departure_date":
                departure.apply_immediately = departure.departure_date <= today
            elif departure.action_at == "other":
                departure.apply_immediately = not departure.action_other_date or departure.action_other_date <= today
            else:
                departure.apply_immediately = False

    @api.depends('action_at', 'departure_date', 'action_other_date')
    def _compute_apply_date(self):
        today = fields.Date.today()
        for departure in self:
            if departure.action_at == 'departure_date':
                departure.apply_date = max(departure.departure_date, today)
            else:
                departure.apply_date = departure.action_other_date or today

    def _check_departure_validity(self):
        for departure in self:
            active_version = departure.employee_id.current_version_id
            if active_version.contract_date_start and active_version.contract_date_start > departure.departure_date:
                raise ValidationError(self.env._("Departure date can't be earlier than the start date of current contract."))

    def create(self, vals_list):
        res = super().create(vals_list)
        for departure in res:
            departure.employee_id._get_version(departure.departure_date).write({
                'departure_id': departure.id,
            })
        return res

    def action_register(self):
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

        self._check_departure_validity()

        departures_per_user = self.grouped('employee_id.user_id')
        to_archive_users = self.env['res.users']
        for user, departures in departures_per_user.items():
            active_user_employees = user.employee_ids.filtered('active')
            if not user.active or (active_user_employees - departures.employee_id):
                # We don't archive the user if all related active employees are not fired
                continue
            if any(lambda d: d.do_archive_user, departures):
                # We don't archive the user if any of the departures related asks to keep it active
                continue
            to_archive_users += user
        if to_archive_users:
            to_archive_users.action_archive()

        for departure in self:
            employee = departure.employee_id
            active_version = employee.version_id

            if departure.apply_date > fields.Date.today():
                raise ValidationError(self.env._("The apply date isn't reached yet."))

            if departure.do_archive_employee and departure.employee_id.active:
                employee.action_archive()

            if departure.do_set_date_end and active_version.contract_date_start:
                active_version.write({'contract_date_end': departure.departure_date})

        self.state = 'done'

    def action_schedule(self):
        self.state = 'scheduled'

    def action_cancel(self):
        self.state = 'cancelled'
        self.employee_id.version_id.departure_id = False

    def action_draft(self):
        self.state = 'draft'

    def _cron_apply_departure(self):
        departures = self.search([
            ('state', '=', 'scheduled'),
            ('apply_date', '<=', fields.Date.today()),
        ])
        for departure in departures:
            departure.action_register()

    def action_register(self):

        employee_ids = self.employee_ids
        active_versions = employee_ids.version_id
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
