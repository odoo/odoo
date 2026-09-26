from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


WEEKDAYS = [
    ('0', 'Monday'),
    ('1', 'Tuesday'),
    ('2', 'Wednesday'),
    ('3', 'Thursday'),
    ('4', 'Friday'),
    ('5', 'Saturday'),
    ('6', 'Sunday'),
]

WEEK_TYPES = [
    ('0', 'Week 1'),
    ('1', 'Week 2'),
]

DAY_LOCATION_FIELDS = [
    'monday_location_id', 'tuesday_location_id', 'wednesday_location_id',
    'thursday_location_id', 'friday_location_id', 'saturday_location_id',
    'sunday_location_id',
]


class PresenlyScheduleGenerateWizard(models.TransientModel):
    _name = 'presenly.schedule.generate.wizard'
    _description = 'Generate Work Locations from Working Hours'

    employee_id = fields.Many2one(
        'hr.employee', required=True, check_company=True,
    )
    company_id = fields.Many2one(
        related='employee_id.company_id', readonly=True,
    )
    calendar_id = fields.Many2one(
        related='employee_id.resource_calendar_id', string='Working Hours',
        readonly=True,
    )
    calendar_two_weeks = fields.Boolean(
        related='calendar_id.two_weeks_calendar', readonly=True,
    )
    generation_mode = fields.Selection([
        ('gaps', 'Fill Unassigned Working Hours'),
        ('replace', 'Replace All Weekly Location Slots'),
    ], required=True, default='gaps')
    default_work_location_id = fields.Many2one(
        'hr.work.location', string='Default Work Location', check_company=True,
        domain="[('active', '=', True), ('company_id', '=', company_id)]",
    )
    check_in_tolerance_minutes = fields.Integer(
        default=30, string='Check-In Tolerance (minutes)',
    )
    line_ids = fields.One2many(
        'presenly.schedule.generate.wizard.line', 'wizard_id',
        string='Location Assignment Preview',
    )
    line_count = fields.Integer(compute='_compute_line_count')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for wizard in self:
            wizard.line_count = len(wizard.line_ids)

    @api.model
    def default_get(self, field_names):
        values = super().default_get(field_names)
        employee = self.env['hr.employee'].browse(
            values.get('employee_id') or self.env.context.get('default_employee_id')
        ).exists()
        if employee:
            values.setdefault('employee_id', employee.id)
            values.setdefault(
                'default_work_location_id', employee.work_location_id.id
            )
        return values

    @api.onchange(
        'employee_id', 'generation_mode', 'default_work_location_id'
    )
    def _onchange_generation_options(self):
        self._prepare_lines()

    def _default_location(self, weekday):
        self.ensure_one()
        if self.default_work_location_id:
            return self.default_work_location_id
        employee = self.employee_id
        daily = employee[DAY_LOCATION_FIELDS[int(weekday)]]
        if daily and daily.company_id == employee.company_id:
            return daily
        return employee.work_location_id

    def _gap_periods(self):
        self.ensure_one()
        schedule_model = self.env['presenly.work.location.schedule']
        periods = schedule_model._calendar_template_periods(self.employee_id)
        if self.generation_mode == 'replace':
            return periods

        weekly_slots = self.employee_id.presenly_schedule_ids.filtered(
            lambda slot: slot.active
            and slot.schedule_type == 'weekly'
            and slot._presenly_is_within_working_hours()
        )
        gaps = []
        for period in periods:
            matching = weekly_slots.filtered(
                lambda slot: slot.weekday == period['weekday']
                and (slot.week_type or False) == (period['week_type'] or False)
                and slot.hour_from < period['hour_to']
                and slot.hour_to > period['hour_from']
            )
            cursor = period['hour_from']
            for slot in matching.sorted('hour_from'):
                if slot.hour_from > cursor + 0.000001:
                    gaps.append({
                        **period,
                        'hour_from': cursor,
                        'hour_to': min(slot.hour_from, period['hour_to']),
                    })
                cursor = max(cursor, min(slot.hour_to, period['hour_to']))
            if cursor < period['hour_to'] - 0.000001:
                gaps.append({
                    **period,
                    'hour_from': cursor,
                    'hour_to': period['hour_to'],
                })
        return gaps

    def _prepare_lines(self):
        self.ensure_one()
        self.line_ids = [(5, 0, 0)]
        if not self.employee_id:
            return
        calendar = self.employee_id.resource_calendar_id
        if not calendar or calendar.flexible_hours:
            return
        commands = []
        for period in self._gap_periods():
            location = self._default_location(period['weekday'])
            commands.append((0, 0, {
                'weekday': period['weekday'],
                'week_type': period['week_type'],
                'hour_from': period['hour_from'],
                'hour_to': period['hour_to'],
                'work_location_id': location.id,
            }))
        self.line_ids = commands

    @api.constrains('check_in_tolerance_minutes')
    def _check_tolerance(self):
        if any(wizard.check_in_tolerance_minutes < 0 for wizard in self):
            raise ValidationError('Check-in tolerance cannot be negative.')

    def action_generate(self):
        self.ensure_one()
        calendar = self.calendar_id
        if not calendar:
            raise UserError(
                'Select Working Hours on the Employee before generating locations.'
            )
        if calendar.flexible_hours:
            raise UserError(
                'Flexible Working Hours do not contain fixed periods to generate. '
                'Use the primary or native daily Work Location fallback.'
            )
        if not self.line_ids:
            raise UserError(
                'There are no unassigned Working Hours periods to generate.'
                if self.generation_mode == 'gaps'
                else 'The Working Hours calendar has no fixed work periods.'
            )
        missing = self.line_ids.filtered(lambda line: not line.work_location_id)
        if missing:
            raise ValidationError(
                'Select a Work Location for every preview line before generating.'
            )
        wrong_company = self.line_ids.filtered(
            lambda line: line.work_location_id.company_id != self.company_id
        )
        if wrong_company:
            raise ValidationError(
                'Every Work Location must belong to the Employee company.'
            )

        schedule_model = self.env['presenly.work.location.schedule']
        if self.generation_mode == 'replace':
            self.employee_id.presenly_schedule_ids.filtered(
                lambda slot: slot.schedule_type == 'weekly'
            ).unlink()
        schedule_model.create([{
            'employee_id': self.employee_id.id,
            'work_location_id': line.work_location_id.id,
            'schedule_type': 'weekly',
            'weekday': line.weekday,
            'week_type': line.week_type or False,
            'hour_from': line.hour_from,
            'hour_to': line.hour_to,
            'check_in_tolerance_minutes': self.check_in_tolerance_minutes,
        } for line in self.line_ids])
        return self.employee_id.action_open_presenly_schedules()


class PresenlyScheduleGenerateWizardLine(models.TransientModel):
    _name = 'presenly.schedule.generate.wizard.line'
    _description = 'Generated Work Location Preview Line'
    _order = 'weekday, week_type, hour_from, id'

    wizard_id = fields.Many2one(
        'presenly.schedule.generate.wizard', required=True, ondelete='cascade',
    )
    company_id = fields.Many2one(
        related='wizard_id.company_id', readonly=True,
    )
    weekday = fields.Selection(WEEKDAYS, required=True)
    week_type = fields.Selection(WEEK_TYPES, string='Calendar Week')
    hour_from = fields.Float(string='Start Time', required=True)
    hour_to = fields.Float(string='End Time', required=True)
    work_location_id = fields.Many2one(
        'hr.work.location', string='Work Location', check_company=True,
        domain="[('active', '=', True), ('company_id', '=', company_id)]",
    )
