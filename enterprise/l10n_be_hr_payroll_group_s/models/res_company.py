# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    group_s_code = fields.Char("Group S Affiliation Number", groups="hr.group_hr_user")
    group_s_sequence_number = fields.Integer(
        "Group S Sequence Number", groups="hr.group_hr_user", default=0)

    @api.constrains('group_s_code')
    def _check_group_s_code(self):
        if self.group_s_code and len(self.group_s_code) != 6:
            raise ValidationError(_('The code should have 6 characters!'))

    @api.constrains('group_s_sequence_number')
    def _check_group_s_sequence_number(self):
        for company in self:
            if company.group_s_sequence_number < 0:
                raise ValidationError(_('The sequence number should be positive!'))
