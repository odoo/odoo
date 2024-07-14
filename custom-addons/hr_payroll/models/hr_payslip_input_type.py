# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class HrPayslipInputType(models.Model):
    _name = 'hr.payslip.input.type'
    _description = 'Payslip Input Type'

    name = fields.Char(string='Description', required=True)
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    struct_ids = fields.Many2many('hr.payroll.structure', string='Availability in Structure', help='This input will be only available in those structure. If empty, it will be available in all payslip.')
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.company.country_id)
    country_code = fields.Char(related='country_id.code')

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        external_ids = self.get_external_id()
        for input_type in self:
            external_id = external_ids[input_type.id]
            if external_id and not external_id.startswith('__export__'):
                raise UserError(_("You cannot delete %s as it is used in another module but you can archive it instead.", input_type.name))
