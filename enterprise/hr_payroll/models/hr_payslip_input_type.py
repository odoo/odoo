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
    active = fields.Boolean('Active', default=True)
    available_in_attachments = fields.Boolean(string="Available in adjustments")
    is_quantity = fields.Boolean(default=False, string="Is quantity?", help="If set, hide currency and consider the manual input as a quantity for every rule computation using this input.")
    default_no_end_date = fields.Boolean("No end date by default")

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        external_ids = self.get_external_id()
        for input_type in self:
            external_id = external_ids[input_type.id]
            if external_id and not external_id.startswith('__export__'):
                raise UserError(_("You cannot delete %s as it is used in another module but you can archive it instead.", input_type.name))

    @api.constrains('active')
    def _check_salary_attachment_type_active(self):
        if self.env['hr.salary.attachment'].search_count([('other_input_type_id', 'in', self.ids), ('state', 'not in', ('close', 'cancel'))], limit=1):
            raise UserError("You cannot archive an input type if there exists a running salary attachment of this type.")
