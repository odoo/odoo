# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    partena_code = fields.Char("Partena Affiliation Number", groups="hr.group_hr_user")
    partena_sequence_number = fields.Integer(
        "Partena Sequence Number", groups="hr.group_hr_user", default=0)

    @api.constrains('partena_code')
    def _check_partena_code(self):
        if any(company.partena_code and len(company.partena_code) != 6 for company in self):
            raise ValidationError(_('The code should have 6 characters!'))

    @api.constrains('partena_sequence_number')
    def _check_partena_sequence_number(self):
        if any(company.partena_sequence_number < 0 for company in self):
            raise ValidationError(_('The sequence number should be positive!'))
