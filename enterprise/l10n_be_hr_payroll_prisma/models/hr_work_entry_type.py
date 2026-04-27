# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    prisma_code = fields.Char("Prisma code", groups="hr.group_hr_user")

    @api.constrains('prisma_code')
    def _check_prisma_code(self):
        if any(we.prisma_code and not (1 < len(we.prisma_code) < 5) for we in self):
            raise ValidationError(_('The Prisma code must be between 2 and 4 characters long.'))
