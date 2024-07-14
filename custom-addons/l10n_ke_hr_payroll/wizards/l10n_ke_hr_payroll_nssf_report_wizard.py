# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nKeHrPayrollNssfReportWizard(models.TransientModel):
    _name = 'l10n.ke.hr.payroll.nssf.report.wizard'
    _description = 'NSSF Report Wizard'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != 'KE':
            raise UserError(_('You must be logged in a Kenyan company to use this feature'))
        return super().default_get(field_list)

    def _get_year_selection(self):
        current_year = datetime.now().year
        return [(str(i), i) for i in range(1990, current_year + 1)]

    reference_month = fields.Selection(
        [
            ('1', 'January'),
            ('2', 'February'),
            ('3', 'March'),
            ('4', 'April'),
            ('5', 'May'),
            ('6', 'June'),
            ('7', 'July'),
            ('8', 'August'),
            ('9', 'September'),
            ('10', 'October'),
            ('11', 'November'),
            ('12', 'December'),
        ],
        string='Month',
        required=True,
        default=lambda self: str((date.today() - relativedelta(months=1)).month))
    reference_year = fields.Selection(
        selection='_get_year_selection',
        string='Year',
        required=True,
        default=lambda self: str((date.today() - relativedelta(months=1)).year))
    name = fields.Char(
        compute='_compute_name',
        readonly=False,
        store=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company)

    line_ids = fields.One2many(
        'l10n.ke.hr.payroll.nssf.report.line.wizard', 'wizard_id',
        compute='_compute_line_ids', store=True, readonly=False)

    @api.depends('reference_month', 'reference_year')
    def _compute_name(self):
        for wizard in self:
            month = wizard.reference_month
            year = wizard.reference_year
            wizard.name = _('NSSF Report - %(month)s %(year)s', month=month, year=year)

    @api.depends('reference_year', 'reference_month')
    def _compute_line_ids(self):
        for wizard in self:
            payslips = self.env['hr.payslip'].search([
                ('date_from', '>=', date(int(wizard.reference_year), int(wizard.reference_month), 1)),
                ('date_to', '<=', date(int(wizard.reference_year), int(wizard.reference_month), 1) + relativedelta(day=31)),
                ('state', 'in', ['done', 'paid']),
                ('company_id', '=', wizard.company_id.id),
            ])
            result = [(5, 0, 0)]
            for payslip in payslips:
                for line in payslip.line_ids:
                    if line.code.startswith('NSSF_EMPLOYEE_TIER_'):
                        nssf_code = "10" + line.code[-1]
                        result.append((0, 0, {
                            'employee_id': payslip.employee_id.id,
                            'employee_identification_id': payslip.employee_id.identification_id,
                            'employee_kra_pin': payslip.employee_id.l10n_ke_kra_pin,
                            'employee_nssf_number': payslip.employee_id.l10n_ke_nssf_number,
                            'payslip_number': payslip.number,
                            'payslip_nssf_code': nssf_code,
                            'payslip_nssf_amount_employee': line.amount,
                            'payslip_nssf_amount_employer': line.amount,
                            'payslip_income': payslip._get_salary_line_total('GROSS'),
                        }))
            wizard.line_ids = result

    def action_export_xlsx(self):
        self.ensure_one()
        return {
            'name': _('Export NSSF Report into XLSX'),
            'type': 'ir.actions.act_url',
            'url': '/export/nssf/%s' % (self.id),
        }

class L10nKeHrPayrollNssfReportLineWizard(models.TransientModel):
    _name = 'l10n.ke.hr.payroll.nssf.report.line.wizard'
    _description = 'NSSF Report Wizard Line'

    wizard_id = fields.Many2one('l10n.ke.hr.payroll.nssf.report.wizard')
    employee_id = fields.Many2one('hr.employee', required=True)
    employee_identification_id = fields.Char(related='employee_id.identification_id', readonly=True)
    employee_kra_pin = fields.Char(related='employee_id.l10n_ke_kra_pin')
    employee_nssf_number = fields.Char(related='employee_id.l10n_ke_nssf_number')
    payslip_number = fields.Char(string='Payslip Number', required=True)
    payslip_nssf_code = fields.Char(string='NSSF Code')
    payslip_nssf_amount_employee = fields.Float(string='NSSF Amount Employee')
    payslip_nssf_amount_employer = fields.Float(string='NSSF Amount Employer')
    payslip_income = fields.Float(string='Income')
