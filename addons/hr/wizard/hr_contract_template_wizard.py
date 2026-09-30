# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrDepartureWizard(models.TransientModel):
    _name = 'hr.version.wizard'
    _description = 'Contract Template Wizard'

    contract_template_id = fields.Many2one(
            'hr.version', string="Contract Template", groups="hr.group_hr_user", required=True,
            domain=lambda self: [('company_id', '=', self.env.company.id), ('employee_id', '=', False)],
            help="Select a contract template to auto-fill the contract form with predefined values. You can still edit the fields as needed after applying the template.")

    def action_load_template(self):
        employee_id = self.env.context.get('active_id')
        if not employee_id or not self.contract_template_id:
            return
        employee = self.env['hr.employee'].browse(employee_id)
        Version = self.env['hr.version']
        whitelist = Version._get_whitelist_fields_from_template()
        contract_template_vals = self.contract_template_id.copy_data()[0]
        val_list = {
            field: value
                for field, value in contract_template_vals.items()
                if field in whitelist and not self.env['hr.version']._fields[field].related
        }
        employee.write(val_list)
        employee.version_id.contract_template_id = self.contract_template_id
        return
