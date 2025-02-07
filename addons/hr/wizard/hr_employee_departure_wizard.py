# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployeeDepartureWizard(models.TransientModel):
    _name = "hr.employee.departure.wizard"
    _description = "Employee Departure"
    _rec_name = "employee_id"

    def _get_employee_departure_date(self):
        return self.env['hr.employee'].browse(self.env.context['active_id']).departure_date

    def _get_default_departure_date(self):
        departure_date = False
        if self.env.context.get('active_id'):
            departure_date = self._get_employee_departure_date()
        return departure_date or fields.Date.today()

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        default=lambda self: self.env.context.get('active_id', None))
    departure_reason_id = fields.Many2one(
        "hr.departure.reason",
        string="End Reason",
        default=lambda self: self.env['hr.departure.reason'].search([], limit=1),
        required=True)
    departure_description = fields.Html(string="Additional Information")
    departure_date = fields.Date(
        string="Departure Date",
        default=_get_default_departure_date,
        required=True)
    do_archive_employee = fields.Boolean(default=True)
    action_at = fields.Selection([
        ('departure_date', 'Departure Date'),
        ('other', 'Other Date'),
    ], default='departure_date', required=True)
    action_other_date = fields.Date()
    has_selected_actions = fields.Boolean(compute='_compute_has_selected_actions')
    company_id = fields.Many2one('res.company', related='employee_id.company_id')
    country_id = fields.Many2one('res.country', related='company_id.country_id')
    country_code = fields.Char(related="country_id.code", depends=['country_id'])
    apply_immediately = fields.Boolean(compute="_compute_apply_immediately")
    apply_date = fields.Date(compute='_compute_apply_date', store=True)

    def _get_departure_values(self):
        self.ensure_one()
        today = fields.Date.today()
        return {
            'departure_reason_id': self.departure_reason_id,
            'departure_description': self.departure_description,
            'departure_date': self.departure_date,
            'departure_do_archive': self.do_archive_employee,
            'departure_action_at': self.action_at,
            'departure_action_other_date': self.action_other_date,
            'departure_apply_date': self.apply_date or today,
            'departure_applied': False,
        }

    def action_register_departure(self):
        for wizard in self:
            employee = wizard.employee_id
            departure_values = wizard._get_departure_values()
            employee.write(departure_values)
            if wizard.apply_immediately:
                employee._register_departure()

    def _get_action_fields(self):
        return [f for f in self._fields if f.startswith('do_')]

    @api.depends(lambda self: self._get_action_fields())
    def _compute_has_selected_actions(self):
        action_fields = self._get_action_fields()
        for departure in self:
            departure.has_selected_actions = any(departure[field] for field in action_fields)

    @api.depends('action_at', 'departure_date', 'action_other_date')
    def _compute_apply_immediately(self):
        today = fields.Date.today()
        for departure in self:
            if departure.action_at == "departure_date":
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
