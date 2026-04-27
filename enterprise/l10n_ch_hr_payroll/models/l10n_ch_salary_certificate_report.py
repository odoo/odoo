# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import uuid
from collections import defaultdict
import base64
from lxml import etree
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

RULE_MAPPING = {
    '1': 'Income',
    '2.1': 'FringeBenefits/FoodLodging',
    '2.2': 'FringeBenefits/CompanyCar',
    '2.3': 'FringeBenefits/Other',
    '3': 'SporadicBenefits',
    '4': 'CapitalPayment',
    '5': 'OwnershipRight',
    '6': 'BoardOfDirectorsRemuneration',
    '7': 'OtherBenefits',
    '8': 'GrossIncome',
    '9': 'AHV-ALV-NBUV-AVS-AC-AANP-Contribution',
    '10.1': 'BVG-LPP-Contribution/Regular',
    '10.2': 'BVG-LPP-Contribution/Purchase',
    '11': 'NetIncome',
    '12': 'DeductionAtSource',
    '13': 'Charges',
    '13.1': 'Charges/Effective',
    '13.1.1': 'Charges/Effective/TravelFoodAccommodation',
    '13.1.2': 'Charges/Effective/Other',
    '13.2': 'Charges/LumpSum',
    '13.2.1': 'Charges/LumpSum/Representation',
    '13.2.2': 'Charges/LumpSum/Car',
    '13.2.3': 'Charges/LumpSum/Other',
    '13.3': 'Charges/Education',
    '14': 'OtherFringeBenefits',
}


class L10nCHSalaryCertificate(models.Model):
    _name = 'l10n.ch.salary.certificate'
    _description = 'Salary Certificate By Employee'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "CH":
            raise UserError(_('You must be logged in a Swiss company to use this feature'))
        return super().default_get(field_list)

    name = fields.Char(
        string="Description", required=True, compute='_compute_name', readonly=False, store=True)
    year = fields.Integer(required=True, default=lambda self: fields.Date.today().year)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    xml_file = fields.Binary()
    xml_filename = fields.Char()

    def _country_restriction(self):
        return 'CH'

    @api.depends('year')
    def _compute_name(self):
        for sheet in self:
            sheet.name = _('Salary Certificates - Year %s', sheet.year)

    def _get_grouped_salary_certificate_lines(self, line_ids):
        line_ids_tuple = tuple(line_ids)

        # Execute the SQL query with the properly formatted line_ids_tuple
        self.env.cr.execute("""
            SELECT SUM(total),
                   sr.l10n_ch_salary_certificate,
                   pl.employee_id,
                   string_agg(DISTINCT sr.id::character varying, ',') AS salary_rule_ids
            FROM hr_payslip_line pl
            JOIN hr_salary_rule sr ON pl.salary_rule_id = sr.id
            WHERE sr.l10n_ch_salary_certificate <> '' AND pl.id IN %s
            GROUP BY pl.employee_id, sr.l10n_ch_salary_certificate
        """, (line_ids_tuple,))

        return self.env.cr.dictfetchall()

    def _get_rendering_data(self):
        self.ensure_one()

        payslips = self.env['hr.payslip'].search([
            ('state', 'in', ['done', 'paid']),
            ('company_id', '=', self.company_id.id),
            ('date_from', '>=', date(self.year, 1, 1)),
            ('date_to', '<=', date(self.year, 12, 31)),
            ('l10n_ch_avs_status', 'not in', ['young', 'exempted'])
        ])
        employees = payslips.mapped('employee_id')
        lines = payslips.line_ids
        salary_certificate_lines = self._get_grouped_salary_certificate_lines(lines.ids)
        mapped_lines = defaultdict(lambda: {
                'Income': [0, ''],
                'FringeBenefits': {
                    'FoodLodging': [0, ''],
                    'CompanyCar': [0, ''],
                    'Other': [0, '']
                },
                'SporadicBenefits': [0, ''],
                'CapitalPayment': [0, ''],
                'OwnershipRight': [0, ''],
                'BoardOfDirectorsRemuneration': [0, ''],
                'OtherBenefits': [0, ''],
                'GrossIncome': [0, ''],
                'AHV-ALV-NBUV-AVS-AC-AANP-Contribution': [0, ''],
                'BVG-LPP-Contribution': {
                    'Regular': [0, ''],
                    'Purchase': [0, '']
                },
                'NetIncome': [0, ''],
                'DeductionAtSource': [0, ''],
                'Charges': {
                    'Effective': {
                        'TravelFoodAccommodation': [0, ''],
                        'Other': [0, '']
                    },
                    'LumpSum': {
                        'Representation': [0, ''],
                        'Car': [0, ''],
                        'Other': [0, '']
                    },
                    'Education': [0, '']
                },
                'OtherFringeBenefits': [0, '']
            })

        for s_c_l in salary_certificate_lines:
            salary_certificate_category = RULE_MAPPING[s_c_l['l10n_ch_salary_certificate']]
            keys = salary_certificate_category.split('/')
            d_val = mapped_lines[s_c_l['employee_id']]
            salary_rule_names = ','.join(self.env['hr.salary.rule'].browse([int(s_id) for s_id in s_c_l['salary_rule_ids'].split(',')]).mapped('name'))
            for key in keys[:-1]:
                d_val = d_val.get(key)
            d_val[keys[-1]][0] = "{:.2f}".format(s_c_l['sum'])
            d_val[keys[-1]][1] = salary_rule_names

        return {
            'creation_date': fields.Datetime.now(),
            'accounting_period': self.year,
            'contact_person': self.env.ref("base.partner_admin"),
            'employee_data': [{
                'DocID': uuid.uuid4(),
                'salaries': mapped_lines[emp.id],
                'sv-as-number': emp.l10n_ch_sv_as_number or 'unknown',
                'Lastname': ' '.join(re.sub(r"\([^()]*\)", "", emp.name).strip().split()[:-1]),
                'Firstname': re.sub(r"\([^()]*\)", "", emp.name).strip().split()[-1],
                'sex': 'M' if emp.gender == 'male' else 'F',
                'nationality': emp.country_id.code,
                'Street': emp.private_street or "",
                'ZIP-Code': emp.private_zip,
                'City': emp.private_city,
                'Country': (emp.private_country_id.name or "").upper(),
                'ResidenceCanton': emp.l10n_ch_canton,
                'MunicipalityID': emp.l10n_ch_municipality or "",
                'birthday': emp.birthday,
                'emp_number': emp.id,
                'year': self.year,
                'period_from': max(emp.first_contract_date, date(self.year, 1, 1)),
                'period_until': min(emp.departure_date, date(self.year, 12, 31)) if emp.departure_date else date(self.year, 12, 31)
            } for emp in employees],
            'company': self.company_id
        }

    def action_generate_xml(self):
        self.xml_filename = '%s-salary-certificates.xml' % (self.year)
        report = self.env['ir.qweb']._render('l10n_ch_hr_payroll.l10n_ch_salary_certificate_report_xml', self._get_rendering_data())
        root = etree.fromstring(report, parser=etree.XMLParser(remove_blank_text=True, resolve_entities=False))
        xml_str = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True)
        self.xml_file = base64.b64encode(xml_str)
