# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrJob(models.Model):
    _inherit = 'hr.job'

    l10n_be_contract_ip = fields.Boolean(string="Intellectual Property", help="If checked, the job position is eligible to Intellectual Property")
    l10n_be_contract_withholding_taxes_exemption = fields.Boolean(string="Withholding Taxes Exemption", help="If checked, the job position will grant a withholding taxes exemption to eligible employees")

    l10n_be_custom_representation_fees = fields.Boolean(string="Customized Representation Fees", help="""If you check this field, you can select various advantages to set the threshold in the representation fees.\n Amount above the representation fee threshold is called "Representation fees without serious standard" and can be prorated according to the employee working rate""")
    l10n_be_custom_representation_fees_homeworking = fields.Boolean(string="Homeworking")
    l10n_be_custom_representation_fees_phone = fields.Boolean(string="Phone")
    l10n_be_custom_representation_fees_internet = fields.Boolean(string="Internet")
    l10n_be_custom_representation_fees_car_management = fields.Boolean(string="Car Management")


    @api.model
    def action_hr_job_payroll_configuration(self):
        if self.env.company.country_id.code == 'BE':
            view = self.env.ref('l10n_be_hr_contract_salary.l10n_be_hr_job_payroll_view_tree')
        else:
            view = self.env.ref('l10n_be_hr_contract_salary.hr_job_payroll_view_tree')
        action = {
            'name': _('Job Position'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.job',
            'views': [(view.id, 'tree'), (False, 'form')],
            'view_id': view.id,
            'view_mode': 'tree',
        }
        return action
