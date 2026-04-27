# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HRContract(models.Model):
    _inherit = 'hr.contract'

    l10n_eg_housing_allowance = fields.Monetary(string='Egypt Housing Allowance')
    l10n_eg_transportation_allowance = fields.Monetary(string='Egypt Transportation Allowance')
    l10n_eg_other_allowances = fields.Monetary(string='Egypt Other Allowances')
    l10n_eg_number_of_days = fields.Integer(
        string='Provision number of days',
        help='Number of days of basic salary to be added to the end of service provision per year')
    l10n_eg_total_number_of_days = fields.Integer(
        string='Total Number of Days',
        help='Number of days of basic salary to be added to the end of service benefit')
    l10n_eg_total_eos_benefit = fields.Integer(
        string='Total End of service benefit',
        compute='_compute_end_of_service')
    l10n_eg_social_insurance_reference = fields.Monetary(string='Social Insurance Reference Amount')

    @api.depends('l10n_eg_total_number_of_days', 'l10n_eg_other_allowances', 'l10n_eg_transportation_allowance', 'wage')
    def _compute_end_of_service(self):
        for contract in self:
            contract.l10n_eg_total_eos_benefit = ((contract._get_contract_wage() + contract.l10n_eg_transportation_allowance + contract.l10n_eg_other_allowances) / 30) * contract.l10n_eg_total_number_of_days

    _sql_constraints = [
        ('check_l10n_eg_number_of_days_positive', 'CHECK(l10n_eg_number_of_days >= 0)',
         'Provision Number of Days must be equal to or greater than 0'),
        ('check_l10n_eg_total_number_of_days_positive', 'CHECK(l10n_eg_total_number_of_days >= 0)',
         'Benefit Number of Days must be equal to or greater than 0')
    ]
