# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta
from itertools import product

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round


class L10nLuMonthlyDeclarationWizard(models.TransientModel):
    _name = 'l10n.lu.monthly.declaration.wizard'
    _description = "Luxembourg: Monthly Declaration"

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    @api.model
    def _get_year_selection(self):
        end_year = (fields.Date.today() - relativedelta(months=1)).year
        return [
            (str(year), year) for year in range(end_year, end_year - 2, -1)
        ]

    year = fields.Selection(_get_year_selection, required=True, default=lambda self: self._get_year_selection()[0][0])
    month = fields.Selection([
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
    ], required=True, default=lambda self: str((fields.Date.today() - relativedelta(months=1)).month))
    date_start = fields.Date(compute='_compute_dates')
    date_end = fields.Date(compute='_compute_dates')

    batch_ids = fields.Many2many('hr.payslip.run', compute='_compute_batch_ids')

    situational_unemployment_ids = fields.One2many(
        'l10n.lu.situational.unemployment.wizard',
        'monthly_declaration_id',
        compute='_compute_situational_unemployment_ids',
        readonly=False,
        store=True)

    can_generate = fields.Boolean(compute='_compute_can_generate')
    decsal_file = fields.Binary()
    decsal_name = fields.Char(default='DECSAL.dta', store=False)

    @api.depends('month', 'year')
    def _compute_dates(self):
        for wizard in self:
            wizard.date_start = date(int(wizard.year), int(wizard.month), 1)
            wizard.date_end = wizard.date_start + relativedelta(months=1, days=-1)

    @api.depends('company_id', 'month', 'year')
    def _compute_batch_ids(self):
        for wizard in self:

            wizard.batch_ids = self.env['hr.payslip.run'].search([
                ('company_id', '=', wizard.company_id.id),
                ('date_start', '>=', wizard.date_start),
                ('date_end', '<=', wizard.date_end),
                ('state', '!=', 'draft'),
            ])

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "LU":
            raise UserError(_('You must be logged in a Luxembourger company to use this feature'))
        res = super().default_get(field_list)
        return res

    @api.depends('situational_unemployment_ids.amount')
    def _compute_can_generate(self):
        for wizard in self:
            wizard.can_generate = wizard.batch_ids and (not wizard.situational_unemployment_ids or all(wizard.situational_unemployment_ids.mapped('amount')))

    @api.depends('batch_ids')
    def _compute_situational_unemployment_ids(self):
        situational_unemp = self.env.ref('l10n_lu_hr_payroll.work_entry_type_situational_unemployment')
        for wizard in self:
            regular_payslips = wizard.batch_ids.slip_ids.filtered(lambda p: p.struct_id == p.struct_type_id.default_struct_id)
            unemp_payslips = regular_payslips.worked_days_line_ids.filtered(
                lambda w: w.work_entry_type_id.id == situational_unemp.id
            ).payslip_id

            wizard.situational_unemployment_ids = [(5, 0)] + [(0, 0, {
                    'payslip_id': payslip.id,
                    'employee_id': payslip.employee_id.id,
                    'hours': payslip.worked_days_line_ids.filtered(lambda w: w.work_entry_type_id.id == situational_unemp.id).number_of_hours,
                }) for payslip in unemp_payslips
            ]

    def action_generate_declaration(self):
        self.ensure_one()

        company = self.env.company
        if not (company.l10n_lu_official_social_security and company.l10n_lu_seculine):
            raise UserError(_('Missing company\'s social security or SECUline numbers'))

        payslips = self.batch_ids.slip_ids
        employees_no_id = payslips.employee_id.filtered(lambda e: not e.identification_id)
        if employees_no_id:
            raise UserError(_('The following employees are missing an identification number:\n - %s',
                              "\n - ".join(employees_no_id.mapped('name'))))

        if self.situational_unemployment_ids and any(not su.amount for su in self.situational_unemployment_ids):
            raise UserError(_('Missing amounts for situational unemployments'))

        line_values = payslips._get_line_values(self._get_declaration_codes())
        declaration_values = self._get_monthly_declaration_values(payslips, line_values)
        company_values = [f"0;{company.l10n_lu_official_social_security};{company.l10n_lu_seculine}"]

        declaration = "\r\n".join(company_values + [
            ";".join(str(value) for value in declaration.values())
            for declaration in declaration_values
        ])
        self.decsal_file = base64.encodebytes(str.encode(declaration))

        return {
            'name': _('Monthly Salary Declaration (DECSAL)'),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def _get_declaration_codes(self):
        return [
            'BASIC',
            'NET',
        ]

    def _get_monthly_declaration_values(self, payslips, line_values):
        self.ensure_one()

        declaration_values = []
        ref_period = self.date_start.strftime('%Y%m')

        sevenSSM = int(7 * float(self.env['hr.rule.parameter']._get_parameter_from_code('l10n_lu_min_social_pay', self.date_start)) * 100)
        grouped_payslips = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in payslips:
            grouped_payslips[(payslip.employee_id.id, payslip.struct_type_id.id)] |= payslip

        for dummy, payslips in grouped_payslips.items():
            situational_unemployment = self.situational_unemployment_ids.filtered(lambda s: s.payslip_id in payslips)
            regular_payslips = payslips.filtered(lambda p: p.struct_id == p.struct_type_id.default_struct_id)
            gratification_payslips = payslips.filtered(lambda p: p.struct_id.code in ['LUX_GRATIFICATION', 'LUX_13TH_MONTH'])

            worked_hours = int(float_round(sum(regular_payslips.worked_days_line_ids.filtered(lambda w: w.is_paid and w.amount).mapped('number_of_hours')), 0))

            contracts_start = payslips.contract_id.mapped('date_start')
            period_start = max(min(contracts_start), self.date_start)

            all_contracts_end = payslips.contract_id.mapped('date_end')
            if all(d for d in all_contracts_end):
                max_contract_end = max([d for d in all_contracts_end if d])
                period_end = max_contract_end
            else:
                period_end = self.date_end

            basic_wage = int(sum(line_values['BASIC'][p.id]['total'] for p in regular_payslips) * 100)
            total_wage = int(sum(line_values['NET'][p.id]['total'] for p in regular_payslips) * 100)
            complements = int(sum(p._get_category_data('SUPPLEMENTS_ACCESSORIES')['total'] for p in regular_payslips) * 100)
            extra_hours = int(sum(p._get_category_data('OVERTIME_PAY')['quantity'] for p in regular_payslips) * 100)
            extra_hours_amount = int(sum(p._get_category_data('OVERTIME_PAY')['total'] for p in regular_payslips) * 100)
            gratifications = int(sum(line_values['BASIC'][p.id]['total'] for p in gratification_payslips) * 100)

            payslip = payslips[0]
            # Source: https://ccss.public.lu/dam-assets/seculine/traces/ccss-seculine-trace-DECSAL.pdf
            values = {
                "1_declaration_type": 1,
                "2_company_ssn": self.env.company.l10n_lu_official_social_security,
                "3_employee_ssn": payslip.employee_id.identification_id,
                "4_reference_period": ref_period,
                "5_basic_wage_cents": basic_wage,
                "6_worked_hours": worked_hours,
                "7_complements_cents": complements,
                "8_extra_hours_cents": extra_hours_amount,
                "9_extra_hours": extra_hours,
                "10_benefits_cents": gratifications,
                "11_sit_unemp_cents": int((situational_unemployment.amount or 0) * 100),
                "12_sit_unemp_hours": int(situational_unemployment.hours),
                "13_public_sector_cents": 0,
                "14_period_start": period_start.strftime("%d"),
                "15_period_end": period_end.strftime("%d"),
                "16_7ssm": "Y" if total_wage >= sevenSSM else "",
                "17_filler1": "",
                "18_filler2": "",
                "19_filler3": "",
                "20_company_reference": self.env.company.id,
            }
            declaration_values.append(values)
        return declaration_values


class L10nLuSituationalUnemploymentWizard(models.TransientModel):
    _name = 'l10n.lu.situational.unemployment.wizard'
    _description = "Employee Situational Unemployment"

    monthly_declaration_id = fields.Many2one('l10n.lu.monthly.declaration.wizard', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='monthly_declaration_id.company_id')
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id")

    payslip_id = fields.Many2one('hr.payslip')

    employee_id = fields.Many2one('hr.employee', readonly=True)
    hours = fields.Float(readonly=True)
    amount = fields.Monetary(required=True, default=0.0)
