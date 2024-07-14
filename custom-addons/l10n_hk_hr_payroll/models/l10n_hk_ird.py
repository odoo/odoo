# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date
from odoo.tools.misc import file_path


MONTH_SELECTION = [
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
]

class L10nHkIrd(models.AbstractModel):
    _name = 'l10n_hk.ird'
    _inherit = 'hr.payroll.declaration.mixin'
    _description = 'IRD Sheet'
    _order = 'start_period'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != 'HK':
            raise UserError(_('You must be logged in a Hong Kong company to use this feature.'))
        if not self.env.company.l10n_hk_employer_name or not self.env.company.l10n_hk_employer_file_number:
            raise UserError(_("Please configure the Employer's Name and the Employer's File Number in the company settings."))
        return super().default_get(field_list)

    state = fields.Selection([('draft', 'Draft'), ('waiting', 'Waiting'), ('done', 'Done')], default='draft')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    start_year = fields.Integer(required=True, default=lambda self: fields.Date.today().year - 1)
    start_month = fields.Selection(MONTH_SELECTION, required=True, default='4')
    start_period = fields.Date('Start Period', compute='_compute_period', store=True)
    end_year = fields.Integer(required=True, default=lambda self: fields.Date.today().year)
    end_month = fields.Selection(MONTH_SELECTION, required=True, default='3')
    end_period = fields.Date('End Period', compute='_compute_period', store=True)
    submission_date = fields.Date('Submission Date', default=fields.Date.today, required=True)
    year_of_employer_return = fields.Char("Year of Employer's Return")
    name_of_signer = fields.Char("Name of Signer", required=True)
    designation_of_signer = fields.Char("Designation of Signer", required=True)
    type_of_form = fields.Selection(
        [('O', "Original"), ('A', "Additional"), ('R', "Replacement")],
        "Type Of Form", default='O', required=True
    )
    xml_file = fields.Binary(string="XML File")
    xml_filename = fields.Char("XML Filename")
    xml_validation_state = fields.Selection([
        ('normal', 'N/A'),
        ('done', 'Valid'),
        ('invalid', 'Invalid'),
    ], default='normal', compute='_compute_validation_state', store=True)
    error_message = fields.Char('Error Message', compute='_compute_validation_state', store=True)
    pdf_error = fields.Text('PDF Error Message')

    def _country_restriction(self):
        return 'HK'

    @api.constrains('year_of_employer_return')
    def _check_year_of_employer_return(self):
        for report in self.filtered(lambda c: c.year_of_employer_return):
            year = report.year_of_employer_return
            if not year.isdecimal() or len(year) != 4:
                raise UserError(_("The year of employer's return must be a 4 digits number."))
            if int(year) > fields.Date.today().year:
                raise UserError(_("The year of employer's return must be in the past."))

    @api.depends('xml_file')
    def _compute_validation_state(self):
        self.xml_validation_state = 'normal'

    @api.depends('start_year', 'start_month', 'end_year', 'end_month')
    def _compute_period(self):
        for record in self:
            record.start_period = date(record.start_year, int(record.start_month), 1)
            record.end_period = date(record.end_year, int(record.end_month), 1) + relativedelta(day=31)

    @api.depends('start_period')
    def _compute_display_name(self):
        for sheet in self:
            sheet.display_name = format_date(self.env, sheet.start_period, date_format="MMMM y", lang_code=self.env.user.lang)

    @api.model
    def _get_xml_resource(self, file_name):
        return file_path(f'l10n_hk_hr_payroll/data/xml_schema/{file_name}')

    @api.model
    def _check_employees(self, employees):
        if not employees:
            return _("You must select at least one employee.")
        error_messages = []
        invalid_employees = employees.filtered(lambda e: not e.private_street or not e.private_state_id)
        if invalid_employees:
            error_messages.append(_("The following employees don't have a valid private address (with a street and a state): %s", ', '.join(invalid_employees.mapped('name'))))
        invalid_employees = employees.filtered(lambda e: not e.l10n_hk_surname or not e.l10n_hk_given_name or not e.gender)
        if invalid_employees:
            error_messages.append(_("Please configure a surname, a given name and a gender for the following employees: %s", ', '.join(invalid_employees.mapped('name'))))
        invalid_employees = employees.filtered(lambda e: not e.identification_id and not e.passport_id)
        if invalid_employees:
            error_messages.append(_("Please configure a HKID or a passport number for the following employees: %s", ', '.join(invalid_employees.mapped('name'))))
        invalid_employees = employees.filtered(lambda emp: not emp.contract_ids or not emp.contract_id)
        for employee in invalid_employees:
            history = self.env['hr.contract.history'].search([('employee_id', '=', employee.id)], limit=1)
            contracts = history.contract_ids.filtered(lambda c: c.active and c.state in ['open', 'close'])[0]
            employee.contract_id = contracts[0] if contracts else False
        invalid_employees = employees.filtered(lambda emp: not emp.contract_ids or not emp.contract_id)
        if invalid_employees:
            error_messages.append(_("Some employee don't have any contract.:\n%s", '\n'.join(invalid_employees.mapped('name'))))
        invalid_employees = employees.filtered(lambda emp: len(emp.l10n_hk_rental_ids.filtered_domain([
            ('state', 'in', ['open', 'close']),
            ('date_start', '<=', self.end_period),
            '|', ('date_end', '>', self.start_period), ('date_end', '=', False),
        ])) > 2)
        if invalid_employees:
            error_messages.append(_("Some employee have more than 2 rental records within the period:\n%s", '\n'.join(invalid_employees.mapped('name'))))
        return '\n'.join(error_messages)

    def _get_main_data(self):
        self.ensure_one()
        company = self.company_id
        file_number = company.l10n_hk_employer_file_number.strip()
        section, ern = file_number.split('-')
        company_address = ', '.join(i for i in [company.street, company.street2, company.city, company.state_id.name, company.country_id.name] if i)
        return {
            'FileNo': file_number,
            'Section': section,
            'ERN': ern.upper(),
            'YrErReturn': self.year_of_employer_return if self.type_of_form == 'O' else '',
            'SubDate': self.submission_date,
            'ErName': company.l10n_hk_employer_name,
            'company_address': company_address,
            'NAME_OF_SIGNER': self.name_of_signer,
            'Designation': self.designation_of_signer,
        }
