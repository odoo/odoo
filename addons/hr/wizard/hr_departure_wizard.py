# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrDepartureWizard(models.TransientModel):
    _name = 'hr.departure.wizard'
    _description = 'Departure Wizard'

    def _get_default_employee_ids(self):
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            return self.env['hr.employee'].browse(active_ids).filtered(lambda e: e.company_id in self.env.companies)
        return self.env['hr.employee']

    def _get_domain_employee_ids(self):
        return [('active', '=', True), ('company_id', 'in', self.env.companies.ids)]

    employee_ids = fields.Many2many(
        'hr.employee', string='Employees', required=True,
        default=_get_default_employee_ids,
        context={'active_test': False},
        domain=_get_domain_employee_ids,
    )
    country_codes = fields.Char(compute="_compute_country_codes")
    departure_reason_id = fields.Many2one(
        "hr.departure.reason",
        string="End Reason",
        default=lambda self: self.env['hr.departure.reason'].search([], limit=1),
        required=True, ondelete='restrict')
    departure_description = fields.Html(string="Additional Information")
    departure_date = fields.Date(
        string="Departure Date",
        default=fields.Date.today,
        required=True)
    action_at_departure = fields.Boolean(string="Action at", default=True)
    action_other_date = fields.Date(string="Apply date")
    is_user_employee = fields.Boolean(
        compute='_compute_is_user_employee',
        export_string_translation=False,
    )
    do_archive_user = fields.Boolean(
        string="Archive Related User",
        help="""
            If checked, the related user will be removed from the system.
            The user will however not be removed if they still have an employee in any other company after this departure.
        """,
    )
    do_archive_employee = fields.Boolean(default=True, string="Archive Employee")
    do_set_date_end = fields.Boolean(
        string="Set Contract End Date",
        default=lambda self: self.env.user.has_group('hr_contract.group_hr_contract_manager'),
        help="Set the departure date as the contract end date and delete all future versions.")
    has_selected_actions = fields.Boolean(compute='_compute_has_selected_actions')
    apply_immediately = fields.Boolean(compute="_compute_apply_immediately")
    apply_date = fields.Date(compute='_compute_apply_date', store=True)

    @api.depends('employee_ids.user_id')
    def _compute_is_user_employee(self):
        for wizard in self:
            # Check if at least one employee in the wizard has a user and all the employees related to this user are in the wizard
            # This is to ensure that the user is not removed if there are other employees related to it
            related_users = wizard.employee_ids.user_id
            wizard.is_user_employee = bool(related_users)

    def _get_action_fields(self):
        return [f for f in self._fields if f.startswith('do_')]

    @api.depends('employee_ids.company_id.country_id')
    def _compute_country_codes(self):
        for departure in self:
            departure.country_codes = ','.join(departure.mapped('employee_ids.company_id.country_id.country_code'))

    @api.depends(lambda self: self._get_action_fields())
    def _compute_has_selected_actions(self):
        action_fields = self._get_action_fields()
        for departure in self:
            departure.has_selected_actions = any(departure[field] for field in action_fields)

    @api.depends('action_at_departure', 'departure_date', 'action_other_date')
    def _compute_apply_immediately(self):
        today = fields.Date.today()
        for departure in self:
            if departure.action_at_departure:
                departure.apply_immediately = departure.departure_date <= today
            else:
                departure.apply_immediately = not departure.action_other_date or departure.action_other_date <= today

    @api.depends('action_at_departure', 'departure_date', 'action_other_date')
    def _compute_apply_date(self):
        today = fields.Date.today()
        for departure in self:
            if departure.action_at_departure:
                departure.apply_date = max(departure.departure_date, today)
            else:
                departure.apply_date = departure.action_other_date or today

    def _get_departure_values(self):
        res = []
        action_fields = self._get_action_fields()
        for wizard in self:
            default_vals = {
                'departure_reason_id': wizard.departure_reason_id.id,
                'departure_description': wizard.departure_description,
                'departure_date': wizard.departure_date,
                'action_at_departure': wizard.action_at_departure,
                'action_other_date': wizard.action_other_date,
                'apply_date': wizard.apply_date,
            }
            for field in action_fields:
                default_vals[field] = wizard[field]
            for employee in wizard.employee_ids:
                res.append({
                    **default_vals,
                    'employee_id': employee.id,
                })
        return res

    def action_register_departure(self):
        departures = self.env['hr.employee.departure'].create(self._get_departure_values())
        departures.filtered(lambda d: d.apply_immediately).action_register()
