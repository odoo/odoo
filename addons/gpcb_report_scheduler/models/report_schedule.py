# Part of GPCB. See LICENSE file for full copyright and licensing details.

import logging
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ReportSchedule(models.Model):
    _name = 'gpcb.report.schedule'
    _description = 'Recurring Report Schedule'
    _inherit = ['mail.thread']
    _order = 'sequence, name'

    name = fields.Char(string='Schedule Name', required=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company,
    )

    report_type = fields.Selection(
        selection=[
            ('iva_300', 'Formulario 300 (IVA)'),
            ('withholding_350', 'Formulario 350 (Withholding)'),
            ('ica', 'ICA Return'),
            ('income_tax', 'Income Tax Return'),
            ('withholding_cert', 'Withholding Certificates'),
            ('exogenous', 'Exogenous Information'),
            ('balance_sheet', 'Balance Sheet'),
            ('profit_loss', 'Profit & Loss'),
            ('trial_balance', 'Trial Balance'),
        ],
        string='Report Type', required=True, tracking=True,
    )
    frequency = fields.Selection(
        selection=[
            ('monthly', 'Monthly'),
            ('bimonthly', 'Bimonthly'),
            ('quarterly', 'Quarterly'),
            ('annual', 'Annual'),
        ],
        string='Frequency', required=True, default='monthly', tracking=True,
    )
    day_of_month = fields.Integer(
        string='Generation Day',
        default=5,
        help='Day of the month to generate the report (1-28).',
    )
    lead_days = fields.Integer(
        string='Lead Days Before Deadline',
        default=5,
        help='Generate this many days before the filing deadline for review time.',
    )
    auto_send = fields.Boolean(
        string='Auto-Send to Recipients',
        default=False,
        help='Automatically email the report after generation (skip review).',
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('active', 'Active'),
            ('paused', 'Paused'),
        ],
        string='Status', default='active', required=True, tracking=True,
    )

    # Recipients
    recipient_ids = fields.Many2many(
        'res.partner', string='Recipients',
        help='Partners who receive the report by email.',
    )
    notify_channel = fields.Selection(
        selection=[
            ('email', 'Email'),
            ('internal', 'Internal Notification'),
            ('both', 'Both'),
        ],
        string='Notification Channel', default='email',
    )

    # History
    run_ids = fields.One2many(
        'gpcb.report.schedule.run', 'schedule_id', string='Execution History',
    )
    run_count = fields.Integer(compute='_compute_run_count')
    last_run_date = fields.Date(
        string='Last Run', compute='_compute_last_run', store=True,
    )
    next_run_date = fields.Date(
        string='Next Run', compute='_compute_next_run', store=True,
    )

    @api.depends('run_ids')
    def _compute_run_count(self):
        for schedule in self:
            schedule.run_count = len(schedule.run_ids)

    @api.depends('run_ids.create_date')
    def _compute_last_run(self):
        for schedule in self:
            last_run = schedule.run_ids[:1]
            schedule.last_run_date = last_run.create_date.date() if last_run else False

    @api.depends('frequency', 'day_of_month', 'last_run_date')
    def _compute_next_run(self):
        today = fields.Date.context_today(self)
        for schedule in self:
            schedule.next_run_date = schedule._get_next_run_date(today)

    def _get_next_run_date(self, reference_date):
        """Calculate the next run date based on frequency and generation day."""
        day = min(max(self.day_of_month, 1), 28)
        freq_deltas = {
            'monthly': relativedelta(months=1),
            'bimonthly': relativedelta(months=2),
            'quarterly': relativedelta(months=3),
            'annual': relativedelta(years=1),
        }
        delta = freq_deltas.get(self.frequency, relativedelta(months=1))

        # Start from current month's generation day
        try:
            candidate = reference_date.replace(day=day)
        except ValueError:
            candidate = reference_date.replace(day=28)

        if candidate <= reference_date:
            candidate += delta

        return candidate

    def _get_report_period(self, run_date):
        """Determine the reporting period based on run date and frequency.

        Returns (date_from, date_to) for the period being reported.
        """
        # The report covers the period *before* the generation date
        freq_map = {
            'monthly': relativedelta(months=1),
            'bimonthly': relativedelta(months=2),
            'quarterly': relativedelta(months=3),
            'annual': relativedelta(years=1),
        }
        delta = freq_map.get(self.frequency, relativedelta(months=1))
        period_end = (run_date.replace(day=1) - relativedelta(days=1))
        period_start = (period_end + relativedelta(days=1)) - delta
        return period_start, period_end

    # ------------------------------------------------------------------
    # Cron entry point
    # ------------------------------------------------------------------

    @api.model
    def _cron_generate_reports(self):
        """Daily cron: check all active schedules and generate due reports."""
        today = fields.Date.context_today(self)
        schedules = self.search([('state', '=', 'active')])

        for schedule in schedules:
            if schedule.next_run_date and schedule.next_run_date <= today:
                try:
                    schedule._execute_schedule(today)
                except Exception:
                    _logger.exception(
                        'Failed to execute report schedule %s (%s)',
                        schedule.name, schedule.id,
                    )

    def _execute_schedule(self, run_date):
        """Generate a report run for this schedule."""
        self.ensure_one()
        _logger.info('Executing report schedule: %s (type=%s)', self.name, self.report_type)

        period_start, period_end = self._get_report_period(run_date)

        # Create the run record
        run = self.env['gpcb.report.schedule.run'].create({
            'schedule_id': self.id,
            'report_type': self.report_type,
            'date_from': period_start,
            'date_to': period_end,
            'state': 'generated',
        })

        # Generate the report content
        run._generate_report_content()

        # Auto-send if configured
        if self.auto_send and self.recipient_ids:
            run._send_to_recipients()

        return run

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_run_now(self):
        """Manually trigger the schedule to run now."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        run = self._execute_schedule(today)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Report Run'),
            'res_model': 'gpcb.report.schedule.run',
            'res_id': run.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_runs(self):
        """View execution history for this schedule."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Execution History — %s', self.name),
            'res_model': 'gpcb.report.schedule.run',
            'domain': [('schedule_id', '=', self.id)],
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_pause(self):
        self.write({'state': 'paused'})

    def action_activate(self):
        self.write({'state': 'active'})
