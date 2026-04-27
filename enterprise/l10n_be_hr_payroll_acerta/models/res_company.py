# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    acerta_code = fields.Char("Acerta Affiliation Number", groups="hr.group_hr_user")

    @api.constrains('acerta_code')
    def _check_acerta_code(self):
        if any(company.acerta_code and len(company.acerta_code) != 7 for company in self):
            raise ValidationError(_('The code should be 7 characters!'))
