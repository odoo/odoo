# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    prisma_code = fields.Char("Prisma code", groups="hr.group_hr_user", copy=False)

    @api.constrains('prisma_code')
    def _check_prisma_code(self):
        for employee in self:
            if employee.prisma_code and len(employee.prisma_code) != 5:
                if len(employee.prisma_code) > 5:
                    raise ValidationError(self.env._("Prisma codes can't be longer than 5 characters"))
                employee.prisma_code = employee.prisma_code.zfill(5)
