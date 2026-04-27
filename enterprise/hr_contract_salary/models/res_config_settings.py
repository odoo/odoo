# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    access_token_validity = fields.Integer(string='Default Access Token Validity Duration')
    employee_salary_simulator_link_validity = fields.Integer(string='Default Salary Configurator Link Validity Duration For Employees')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            access_token_validity=int(params.get_param('hr_contract_salary.access_token_validity', default=30)),
            employee_salary_simulator_link_validity=int(params.get_param('hr_contract_salary.employee_salary_simulator_link_validity', default=30))
        )
        return res

    def set_values(self):
        super().set_values()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        # get_param is cached, and thus could avoid unnecessary requests if the parameter doesn't change
        if int(IrConfigParameter.get_param("hr_contract_salary.access_token_validity")) != self.access_token_validity:
            IrConfigParameter.set_param("hr_contract_salary.access_token_validity", self.access_token_validity)
        if int(IrConfigParameter.get_param("hr_contract_salary.employee_salary_simulator_link_validity")) != self.employee_salary_simulator_link_validity:
            IrConfigParameter.set_param("hr_contract_salary.employee_salary_simulator_link_validity", self.employee_salary_simulator_link_validity)
