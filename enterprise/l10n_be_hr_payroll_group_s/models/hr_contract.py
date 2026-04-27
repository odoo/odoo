# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    group_s_code = fields.Char("Group S code", groups="hr.group_hr_user", copy=False)

    @api.constrains('group_s_code')
    def _check_group_s_code(self):
        if any(contract.group_s_code and len(contract.group_s_code) != 6 and contract.country_code == 'BE' for contract in self):
            raise ValidationError(_('The Groups S code should have 6 characters!'))
        similar_group_s_codes = dict(self._read_group(
            domain=[
                ('company_id', 'in', self.company_id.ids),
                ('group_s_code', 'in', self.mapped('group_s_code')),
                ('state', 'in', ['open', 'pending']),
            ],
            groupby=['group_s_code'],
            aggregates=['id:recordset'],
        ))
        if any(
            similar_group_s_codes.get(contract.group_s_code)
            and len(similar_group_s_codes[contract.group_s_code]) > 1
            and contract.country_code == 'BE'
            and contract.group_s_code
            for contract in self
        ):
            raise ValidationError(_('The Groups S code should be unique!'))
