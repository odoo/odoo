# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    ucm_code = fields.Char("UCM Affiliation Number", groups="hr.group_hr_user")
    ucm_company_code = fields.Char("UCM folder Number", groups="hr.group_hr_user")

    @api.constrains('ucm_code')
    def _check_ucm_code(self):
        if any(company.ucm_code and len(company.ucm_code) != 6 for company in self):
            raise ValidationError(_('The code should have 6 characters!'))

    @api.constrains('ucm_company_code')
    def _check_ucm_company_code(self):
        if any(company.ucm_company_code and len(company.ucm_company_code) != 5 for company in self):
            raise ValidationError(_('The code should have 5 characters!'))
