# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    prisma_code = fields.Char("Prisma Affiliation Number", groups="hr.group_hr_user")

    @api.constrains('prisma_code')
    def _check_prisma_code(self):
        if any(company.prisma_code and len(company.prisma_code) != 8 for company in self):
            raise ValidationError(_('The code should be 8 characters!'))
