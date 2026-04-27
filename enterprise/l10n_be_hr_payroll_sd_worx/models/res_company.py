# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    sdworx_code = fields.Char("SDWorx code", groups="hr.group_hr_user")

    @api.constrains('sdworx_code')
    def _check_sdworx_code(self):
        invalid_companies = self.filtered(lambda company: company.sdworx_code and len(company.sdworx_code) != 7)
        if invalid_companies:
            error = _("The following companies should have a 7 characters SDWorx code or should be left empty:\n")
            raise ValidationError(error + "\n".join(invalid_companies.mapped('name')))
