# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from collections import defaultdict

class ContractHistory(models.Model):
    _inherit = 'hr.contract.history'

    default_contract_id = fields.Many2one('hr.contract', string='Contract Template', readonly=True,
        help='Default contract used when making an offer to an applicant.')
    reference_yearly_cost = fields.Monetary('Yearly Cost',
        compute='_compute_reference_data',
        help='Total yearly cost of the employee for the employer.')
    reference_monthly_wage = fields.Monetary('Monthly Wage',
        compute='_compute_reference_data',
        help='Wage update with holidays retenues')
    sign_template_id = fields.Many2one('sign.template', string='New Contract Document Template',
        readonly=True, help='Default document that the applicant will have to sign to accept a contract offer.')
    contract_update_template_id = fields.Many2one('sign.template', string='Contract Update Document Template',
        readonly=True, help='Default document that the employee will have to sign to update his contract.')

    @api.depends('contract_ids')
    def _compute_reference_data(self):
        # We use a compute instead of a related in order to be able to overload in country specific apps.
        mapped_employee_contract = defaultdict(lambda: self.env['hr.contract'],
                                               [(c.employee_id, c) for c in self.mapped('contract_id')])
        for history in self:
            if not mapped_employee_contract[history.employee_id]:
                history.reference_monthly_wage = False
                history.reference_yearly_cost = False
                continue
            history.reference_monthly_wage = mapped_employee_contract[history.employee_id]._get_contract_wage()
            history.reference_yearly_cost = mapped_employee_contract[history.employee_id].final_yearly_costs
