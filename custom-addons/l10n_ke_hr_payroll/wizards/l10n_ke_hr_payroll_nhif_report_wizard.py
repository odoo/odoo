# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nKeHrPayrollNhifReportWizard(models.TransientModel):
    _name = 'l10n.ke.hr.payroll.nhif.report.wizard'
    _description = 'NHIF Report Wizard'

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
        'l10n.ke.hr.payroll.nhif.report.line.wizard', 'wizard_id',
        compute='_compute_line_ids', store=True, readonly=False)

    @api.depends('reference_year', 'reference_month')
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
                ('date_to', '<=', date(int(wizard.reference_year), int(wizard.reference_month), 1) + relativedelta(days=31)),
                ('state', 'in', ['done', 'paid']),
                ('company_id', '=', wizard.company_id.id),
            ])
            result = [(5, 0, 0)]
            for payslip in payslips:
                nhif_amount = 0
                for line in payslip.line_ids:
                    if line.code == 'NHIF_AMOUNT':
                        nhif_amount = line.total
                        break

                result.append((0, 0, {
                    'employee_id': payslip.employee_id.id,
                    'employee_identification_id': payslip.employee_id.identification_id,
                    'nhif_number': payslip.employee_id.l10n_ke_nhif_number,
                    'nhif_amount': nhif_amount,
                    'payslip_number': payslip.number,
                }))
            wizard.line_ids = result

    def action_export_xlsx(self):
        self.ensure_one()
        return {
            'name': _('Export NHIF Report into XLSX'),
            'type': 'ir.actions.act_url',
            'url': '/export/nhif/%s' % (self.id),
        }

class L10nKeHrPayrollNhifReportLineWizard(models.TransientModel):
    _name = 'l10n.ke.hr.payroll.nhif.report.line.wizard'
    _description = 'NHIF Report Wizard Line'

    wizard_id = fields.Many2one('l10n.ke.hr.payroll.nhif.report.wizard')
    employee_id = fields.Many2one('hr.employee', required=True)
    employee_identification_id = fields.Char(related='employee_id.identification_id', readonly=True)
    nhif_number = fields.Char(string='NHIF Number')
    nhif_amount = fields.Float(string='NHIF Amount')
    payslip_number = fields.Char(string='Payslip Number')
