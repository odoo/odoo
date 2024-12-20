# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployeeDeparture(models.Model):
    _name = "hr.employee.departure"
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
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')], default="draft", required=True)
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

    def action_register_departure(self):
        self.ensure_one()
        employee = self.employee_id
        if self.do_archive_employee and employee.active:
            employee.action_archive()
        employee.departure_reason_id = self.departure_reason_id
        employee.departure_description = self.departure_description
        employee.departure_date = self.departure_date
        self.state = 'done'

    def action_schedule(self):
        self.state = 'scheduled'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_draft(self):
        self.state = 'draft'

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


    def _cron_apply_departure(self):
        today = fields.Date.today()
        departures = self.env['hr.employee.departure'].search([
            ('state', '=', 'scheduled'),
            ('apply_date', '<=', today),
        ])
        for departure in departures:
            departure.action_register_departure()
