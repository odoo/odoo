# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployeeDeparture(models.Model):
    _name = "hr.employee.departure"
    _description = "Employee Departure"

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
        ondelete="cascade",
    )
    country_code = fields.Char(related="employee_id.company_id.partner_id.country_id.code")
    departure_reason_id = fields.Many2one(
        "hr.departure.reason",
        string="End Reason",
        default=lambda self: self.env['hr.departure.reason'].search([], limit=1),
        required=True, ondelete='restrict')
    departure_description = fields.Html(string="Additional Information")
    dismissal_date = fields.Date(string="Dismissal Date", default=fields.Date.today, required=True,
        help="Date at which the departure process starts. Differs from the actual departure date in case of a notice period.")
    departure_date = fields.Date(string="Departure Date", compute="_compute_departure_date",
        store=True, readonly=False, help="Date at which the departure actually takes place.")
    action_date = fields.Date(string="Archive Employee On", compute="_compute_action_date",
        store=True, help="Date at which the departure actually takes place.")
    is_user_employee = fields.Boolean(
        compute='_compute_is_user_employee',
        export_string_translation=False,
    )
    apply_immediately = fields.Boolean(compute="_compute_apply_immediately")
    apply_date = fields.Date(readonly=True)

    @api.depends('dismissal_date')
    def _compute_departure_date(self):
        # meant to be overriden in case of notice period
        for departure in self:
            departure.departure_date = departure.dismissal_date

    @api.depends('departure_date')
    def _compute_action_date(self):
        for departure in self:
            if not (departure.departure_date and departure.action_date):
                continue
            if departure.action_date < departure.departure_date:
                departure.action_date = departure.departure_date + relativedelta(days=1)

    @api.onchange("departure_date")
    def _onchange_departure_date(self):
        if self.departure_date:
            self.action_date = self.departure_date + relativedelta(days=1)

    @api.depends('employee_id.user_id')
    def _compute_is_user_employee(self):
        for departure in self:
            departure.is_user_employee = bool(departure.employee_id.user_id)

    @api.depends('departure_date', 'action_date')
    def _compute_apply_immediately(self):
        today = fields.Date.today()
        for departure in self:
            if not departure.departure_date:
                departure.apply_immediately = False
            elif departure.action_date:
                departure.apply_immediately = departure.action_date <= today
            else:
                departure.apply_immediately = departure.departure_date < today

    @api.constrains('employee_id')
    def _check_departure_validity(self):
        emps_with_contract_conflict = self.env['hr.employee']
        emps_with_version_conflict = self.env['hr.employee']
        for departure in self:
            active_version_sudo = departure.employee_id.sudo().current_version_id
            if active_version_sudo.contract_date_start and active_version_sudo.contract_date_start > departure.departure_date:
                emps_with_contract_conflict += departure.employee_id
            no_previous_version = not departure.employee_id.version_ids.filtered(
                lambda v: v.date_version < departure.departure_date,
            )
            if no_previous_version:
                emps_with_version_conflict += departure.employee_id
        if emps_with_contract_conflict:
            raise ValidationError(self.env._(
                "Departure date is earlier than the start date of the current contract(s) of %s.",
                ', '.join(emps_with_contract_conflict.mapped('name')),
            ))
        if emps_with_version_conflict:
            raise ValidationError(self.env._(
                "There is no valid version starting before the departure date for %s.",
                ', '.join(emps_with_version_conflict.mapped('name')),
            ))

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for departure in res:
            departure.employee_id._get_version(departure.dismissal_date).write({
                'departure_id': departure.id,
            })
        return res

    def _cron_apply_departure(self):
        today = fields.Date.today()
        departures = self.search([
            ('apply_date', '=', False),
            '|',
                ('action_date', '<=', today),
                '&',
                    ('action_date', '=', False),
                    ('departure_date', '<', today),
        ])
        departures.action_register()

    def action_schedule(self):
        return {'type': 'ir.actions.act_window_close'}

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

        departures_per_user = self.grouped(lambda departure: departure.employee_id.user_id)
        users_to_archive = self.env['res.users']
        users_to_keep_active = self.env['res.users']
        for user, departures in departures_per_user.items():
            if not user:
                continue
            active_user_employees = user.employee_ids.filtered('active')
            if not user.active or (active_user_employees - departures.employee_id):
                # We don't archive the user if all related active employees are not departing
                users_to_keep_active += user
                continue
            users_to_archive += user
        if users_to_archive:
            users_to_archive.sudo().action_archive()

        emp_to_archive = self.env['hr.employee']
        for departure in self:
            employee = departure.employee_id
            apply_date = departure.action_date or departure.departure_date + relativedelta(days=1) or fields.Date.today()
            if apply_date > fields.Date.today():
                raise ValidationError(self.env._(
                    "The apply date isn't reached yet for the departure of %(emp)s.",
                    emp=departure.employee_id.name))

            if departure.employee_id.active:
                emp_to_archive += employee

            if employee.sudo().contract_date_start:
                employee.sudo().write({'contract_date_end': departure.departure_date})
            employee.version_ids.filtered(lambda v: v.date_version > departure.departure_date).unlink()

        emp_to_archive.action_archive()
        self.apply_date = fields.Date.today()

        next_action = {'type': 'ir.actions.act_window_close'}
        if users_to_archive:
            message = self.env._(
                "The following users have been archived: %s",
                ', '.join(users_to_archive.mapped('name')),
            )
            next_action = _get_user_archive_notification_action(message, 'success', next_action)
        if users_to_keep_active:
            message = self.env._(
                "The following users have not been archived as they are still linked to another active employees: %s",
                ', '.join(users_to_keep_active.mapped('name')),
            )
            next_action = _get_user_archive_notification_action(message, 'danger', next_action)

        return next_action
