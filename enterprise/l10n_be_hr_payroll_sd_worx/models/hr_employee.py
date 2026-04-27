# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    sdworx_code = fields.Char("SDWorx code", groups="hr.group_hr_user")

    @api.constrains('sdworx_code')
    def _check_sdworx_code(self):
        invalid_employees = self.filtered(lambda employee: employee.sdworx_code and len(employee.sdworx_code) != 7)
        if invalid_employees:
            error = _("The following employees should have a 7 characters SDWorx code or should be left empty:\n")
            raise ValidationError(error + "\n".join(invalid_employees.mapped('name')))
