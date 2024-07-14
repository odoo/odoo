# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    @api.constrains('name', 'amount')
    def _check_helb_amount(self):
        for line in self:
            helb_min = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('l10n_ke_helb_min', raise_if_not_found=False)
            if line.name == 'HELB' and 0 < line.amount < helb_min:
                raise UserError(_('The HELB deduction value cannot be below %s Ksh.', helb_min))

    def get_payslip_styling_dict(self):
        result = super().get_payslip_styling_dict()
        result.update({
            'INSURANCE_RELIEF': {
                'line_style': 'color:#00A09D;',
                'line_class': 'o_subtotal o_border_bottom',
            },
            'STATUTORY_DED': {
                'line_style': 'color:#00A09D;',
                'line_class': 'o_subtotal o_border_bottom',
            },
            'OTHER_DED': {
                'line_style': 'color:#00A09D;',
                'line_class': 'o_subtotal o_border_bottom',
            },
        })
        return result
