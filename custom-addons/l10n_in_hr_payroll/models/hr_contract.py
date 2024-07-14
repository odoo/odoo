# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo import api, fields, models, _


class HrContract(models.Model):
    """
    Employee contract allows to add different values in fields.
    Fields are used in salary rule computation.
    """
    _inherit = 'hr.contract'

    l10n_in_tds = fields.Float(string='TDS', digits='Payroll',
        help='Amount for Tax Deduction at Source')
    l10n_in_driver_salay = fields.Boolean(string='Driver Salary', help='Check this box if you provide allowance for driver')
    l10n_in_medical_insurance = fields.Float(string='Medical Insurance', digits='Payroll',
        help='Deduction towards company provided medical insurance')
    l10n_in_voluntary_provident_fund = fields.Float(string='Voluntary Provident Fund (%)', digits='Payroll',
        help='VPF is a safe option wherein you can contribute more than the PF ceiling of 12% that has been mandated by the government and VPF computed as percentage(%)')
    l10n_in_house_rent_allowance_metro_nonmetro = fields.Float(string='House Rent Allowance (%)', digits='Payroll',
        help='HRA is an allowance given by the employer to the employee for taking care of his rental or accommodation expenses for metro city it is 50% and for non metro 40%. \nHRA computed as percentage(%)')
    l10n_in_supplementary_allowance = fields.Float(string='Supplementary Allowance', digits='Payroll')
    l10n_in_gratuity = fields.Float(string='Gratuity')
    l10n_in_esic_amount = fields.Float(string='ESIC Amount', digits='Payroll',
        help='Deduction towards company provided ESIC Amount')
    l10n_in_leave_allowance = fields.Float(string='Leave Allowance', digits='Payroll',
        help='Deduction towards company provided Leave Allowance')

    @api.model
    def update_state(self):
        contract_type_id = self.env.ref('l10n_in_hr_payroll.l10n_in_contract_type_probation', raise_if_not_found=False)
        if contract_type_id:
            one_week_ago = fields.Date.today() - timedelta(weeks=1)
            contracts = self.env['hr.contract'].search([
                ('date_end', '=', one_week_ago), ('state', '=', 'open'), ('contract_type_id', '=', contract_type_id.id)
            ])
            for contract in contracts:
                contract.activity_schedule(
                    'note.mail_activity_data_reminder',
                    user_id=contract.hr_responsible_id.id,
                    note=_("End date of %(name)s's contract is today.", name=contract.employee_id.name),
                )
        return super().update_state()
