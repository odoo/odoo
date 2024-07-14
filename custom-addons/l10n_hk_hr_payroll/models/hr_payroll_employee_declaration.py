# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class HrPayrollEmployeeDeclaration(models.Model):
    _inherit = 'hr.payroll.employee.declaration'

    def action_open_ir56g_details(self):
        self.ensure_one()
        if self.res_model != "l10n_hk.ir56g":
            raise UserError(_('Wrong Model'))
        sheet = self.env[self.res_model].browse(self.res_id)
        ir56g_line = sheet.appendice_line_ids.filtered(lambda l: l.employee_id == self.employee_id)
        if not ir56g_line:
            ir56g_line = self.env['l10n_hk.ir56g.line'].create({
                'employee_id': self.employee_id.id,
                'sheet_id': sheet.id
            })
        return {
            'type': 'ir.actions.act_window',
            'name': _('IR56G Line Details'),
            'res_model': 'l10n_hk.ir56g.line',
            'view_mode': 'form',
            'view_id': self.env.ref('l10n_hk_hr_payroll.view_l10n_hk_ir56g_line_form').id,
            'res_id': ir56g_line.id,
            'target': 'new',
        }
