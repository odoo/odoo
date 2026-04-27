# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, ValidationError


class L10nKeHrPayrollShifReportWizard(models.TransientModel):
    _name = 'l10n.ke.hr.payroll.shif.report.wizard'
    _description = 'SHIF (NHIF) Report Wizard'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != 'KE':
            raise UserError(_('You must be logged in a Kenyan company to use this feature'))
        return super().default_get(field_list)

    def _get_year_selection(self):
        current_year = datetime.now().year
        return [(str(i), i) for i in range(1990, current_year + 1)]

    reference_start_date = fields.Char(
        compute='_compute_reference_start_date')
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
        default=str(date.today().month))
    reference_year = fields.Selection(
        selection='_get_year_selection',
        string='Year',
        required=True,
        default=str(date.today().year))
    name = fields.Char(
        compute='_compute_name',
        readonly=False,
        store=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company)
    line_ids = fields.One2many(
        'l10n.ke.hr.payroll.shif.report.line.wizard', 'wizard_id',
        compute='_compute_line_ids', store=True, readonly=False)
    is_nhif = fields.Boolean(compute='_compute_is_nhif')

    @api.depends('reference_month', 'reference_year')
    def _compute_reference_start_date(self):
        for wizard in self:
            wizard.reference_start_date = (
                        date(int(self.reference_year), int(self.reference_month), 10) - relativedelta(
                    months=1)).strftime("%d %B %Y").title()

    @api.depends('reference_month', 'reference_year')
    def _compute_is_nhif(self):
        for wizard in self:
            wizard.is_nhif = date(int(wizard.reference_year), int(wizard.reference_month), 1) < date(2024,10,10)

    @api.depends('reference_year', 'reference_month')
    def _compute_name(self):
        for wizard in self:
            month = wizard.reference_month
            year = wizard.reference_year
            wizard.name = _('NSSF Report - %(month)s %(year)s', month=month, year=year)

    @api.depends('reference_year', 'reference_month')
    def _compute_line_ids(self):
        for wizard in self:
            start_date = date(int(wizard.reference_year), int(wizard.reference_month), 1)
            end_date = start_date + relativedelta(months=1, days=-1)
            payslips = self.env['hr.payslip'].search([
                ('date_to', '>=', start_date),
                ('date_to', '<=', end_date),
                ('state', 'in', ['done', 'paid']),
                ('company_id', '=', wizard.company_id.id),
            ])
            result = [Command.clear()]
            for payslip in payslips:
                shif_or_nhif_amount = 0
                for line in payslip.line_ids:
                    if line.code == ('NHIF_AMOUNT' if wizard.is_nhif else 'SHIF_AMOUNT'):
                        shif_or_nhif_amount = line.total
                        break

                result.append(Command.create({
                    'employee_id': payslip.employee_id.id,
                    'employee_identification_id': payslip.employee_id.identification_id,
                    'shif_or_nhif_number': payslip.employee_id.l10n_ke_nhif_number if wizard.is_nhif else payslip.employee_id.l10n_ke_shif_number,
                    'shif_or_nhif_amount': shif_or_nhif_amount,
                    'payslip_number': payslip.number,
                }))
            wizard.line_ids = result

    def action_export_xlsx(self):
        self.ensure_one()
        return {
            'name': _('Export SHIF Report into XLSX'),
            'type': 'ir.actions.act_url',
            'url': '/export/nhif/%s' % (self.id) if self.is_nhif else '/export/shif/%s' % (self.id),
        }

    @api.constrains("line_ids")
    def check_lines(self):
        for wizard in self:
            if not wizard.line_ids: raise ValidationError(_('You must add at least one Payslip'))
            for line in wizard.line_ids:
                if not line.employee_id.identification_id:
                    raise ValidationError(_('Please enter a valid Identification ID in the Employee Private information'))
                if not line.employee_id.l10n_ke_nhif_number and wizard.is_nhif:
                    raise ValidationError(_("Please enter a valid NHIF number in the Employee Payroll Configuration Tab"))
                if not line.employee_id.l10n_ke_shif_number and not wizard.is_nhif:
                    raise ValidationError(_("Please enter a valid SHIF number in the Employee Payroll Configuration Tab"))

class L10nKeHrPayrollShifReportLineWizard(models.TransientModel):
    _name = 'l10n.ke.hr.payroll.shif.report.line.wizard'
    _description = 'SHIF Report Wizard Line'

    wizard_id = fields.Many2one('l10n.ke.hr.payroll.shif.report.wizard')
    employee_id = fields.Many2one('hr.employee', required=True)
    employee_identification_id = fields.Char(related='employee_id.identification_id', readonly=True)
    shif_or_nhif_number = fields.Char()
    shif_or_nhif_amount = fields.Float()
    payslip_number = fields.Char(string='Payslip Number')
