from datetime import date
import calendar

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CustomPayrollGenerateWizard(models.TransientModel):
    _name = 'custom.payroll.generate.wizard'
    _description = 'Generate Payslips Wizard'

    payroll_batch_id = fields.Many2one('custom.payroll.batch', required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company)
    department_id = fields.Many2one('hr.department')
    job_id = fields.Many2one('hr.job')
    skip_existing = fields.Boolean(string='Skip employees already in this batch', default=True)
    auto_populate_bpjs = fields.Boolean(string='Auto-populate BPJS components', default=True)
    auto_create_basic = fields.Boolean(string='Auto-create basic salary row', default=True)

    preview_line_ids = fields.One2many(
        'custom.payroll.generate.wizard.preview',
        'wizard_id',
        string='Preview',
        compute='_compute_preview_lines',
    )
    preview_count = fields.Integer(string='Employees to Process', compute='_compute_preview')
    currency_id = fields.Many2one(related='company_id.currency_id')

    @api.depends('preview_line_ids')
    def _compute_preview(self):
        for wiz in self:
            wiz.preview_count = len(wiz.preview_line_ids.filtered(lambda line: not line.will_skip))

    @api.depends('department_id', 'job_id', 'skip_existing', 'payroll_batch_id', 'company_id')
    def _compute_preview_lines(self):
        Preview = self.env['custom.payroll.generate.wizard.preview']
        for wiz in self:
            existing_pairs = {
                (s.employee_id.id, s.work_location_id.id)
                for s in wiz.payroll_batch_id.slip_ids
            }
            period_start, period_end = wiz._resolve_period_dates(wiz.payroll_batch_id)
            lines = Preview
            for emp in wiz._get_candidate_employees():
                locations = wiz._employee_locations_for_period(emp, period_start, period_end)
                for loc in locations:
                    wage = emp.version_id.contract_wage if emp.version_id else 0.0
                    will_skip = wiz.skip_existing and (emp.id, loc.id) in existing_pairs
                    lines |= Preview.new({
                        'employee_id': emp.id,
                        'department_id': emp.department_id.id,
                        'job_id': emp.job_id.id,
                        'contract_wage': wage,
                        'work_location_id': loc.id,
                        'work_location_count': len(locations),
                        'will_skip': will_skip,
                    })
            wiz.preview_line_ids = lines

    @api.model
    def _resolve_period_dates(self, batch):
        if not batch or not batch.periode_bulan or not batch.periode_tahun:
            today = fields.Date.context_today(self.env.user)
            return today, today
        try:
            year = int(batch.periode_tahun)
            month = int(batch.periode_bulan)
            start = date(year, month, 1)
            _, last_day = calendar.monthrange(year, month)
            end = date(year, month, last_day)
            return start, end
        except (TypeError, ValueError):
            today = fields.Date.context_today(self.env.user)
            return today, today

    @api.model
    def _employee_locations_for_period(self, employee, period_start, period_end):
        locations = employee._presenly_work_locations_for_period(period_start, period_end)
        if not locations and employee.work_location_id:
            locations = employee.work_location_id
        return locations

    def _get_candidate_employees(self):
        return self._find_candidate_employees(
            self.company_id,
            self.department_id,
            self.job_id,
        )

    def _find_candidate_employees(self, company, department=None, job=None):
        domain = [
            ('company_id', '=', company.id),
            ('active', '=', True),
        ]
        if department:
            domain.append(('department_id', '=', department.id))
        if job:
            domain.append(('job_id', '=', job.id))
        return self.env['hr.employee'].search(domain)

    def action_generate(self):
        self.ensure_one()
        if self.payroll_batch_id.status != 'draft':
            raise UserError(_('Payslips can only be generated while the batch is in Draft status.'))
        if self.payroll_batch_id.company_id != self.company_id:
            raise UserError(_('The wizard company must match the payroll batch company.'))

        existing_pairs = {
            (s.employee_id.id, s.work_location_id.id)
            for s in self.payroll_batch_id.slip_ids
        }
        for line in self.preview_line_ids:
            pair = (line.employee_id.id, line.work_location_id.id)
            if self.skip_existing and (line.will_skip or pair in existing_pairs):
                continue
            if not line.work_location_id:
                continue
            slip = self.env['custom.payroll.slip'].create({
                'payroll_batch_id': self.payroll_batch_id.id,
                'employee_id': line.employee_id.id,
                'work_location_id': line.work_location_id.id,
                'total_gaji_pokok': line.contract_wage,
                'company_id': self.company_id.id,
            })
            slip._auto_populate_basic_salary_and_bpjs(
                auto_create_basic=self.auto_create_basic,
                auto_populate_bpjs=self.auto_populate_bpjs,
            )
            existing_pairs.add(pair)
        return {'type': 'ir.actions.act_window_close'}


class CustomPayrollGenerateWizardPreview(models.TransientModel):
    _name = 'custom.payroll.generate.wizard.preview'
    _description = 'Generate Payslips Wizard Preview Line'

    wizard_id = fields.Many2one('custom.payroll.generate.wizard', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True)
    department_id = fields.Many2one('hr.department')
    job_id = fields.Many2one('hr.job')
    contract_wage = fields.Monetary(currency_field='currency_id')
    work_location_id = fields.Many2one(
        'hr.work.location', string='Work Location',
        check_company=True,
    )
    work_location_count = fields.Integer(string='Location Count', readonly=True)
    will_skip = fields.Boolean(string='Will Skip', readonly=True)
    currency_id = fields.Many2one(related='wizard_id.company_id.currency_id')
