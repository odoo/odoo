#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import api, fields, models

SWISS_LANGUAGES = ["it_IT", "de_DE", "de_CH", "fr_FR", "fr_CH", "en_EN", "en_US"]


class L10nChHrPayrollEmployeeLangWizard(models.TransientModel):
    _name = 'l10n_ch.hr.payroll.employee.lang.wizard'
    _description = 'Change Employee Language'

    def _default_line_ids(self):
        res = []
        if 'employee_ids' in self.env.context:
            res.extend([(0, 0, {'employee_id': employee}) for employee in self.env.context.get('employee_ids')])
        return res

    line_ids = fields.One2many('l10n_ch.hr.payroll.employee.lang.wizard.line', 'wizard_id', string='Lines', default=_default_line_ids)
    slip_ids = fields.Many2many('hr.payslip', store=False)

    def action_validate(self):
        for wizard in self:
            code_to_employee = defaultdict(lambda: self.env['hr.employee'])
            for line in wizard.line_ids:
                code_to_employee[line.lang] |= line.employee_id
            for code, employees in code_to_employee.items():
                employees.write({'lang': code})
        return self.slip_ids.action_payslip_done()

class L10nChHrPayrollEmployeeLangWizardLine(models.TransientModel):
    _name = 'l10n_ch.hr.payroll.employee.lang.wizard.line'
    _description = 'Change Employee Language Line'

    @api.model
    def _lang_get(self):
        return list(filter(lambda tpl: tpl[0] in SWISS_LANGUAGES, self.env['res.lang'].get_installed()))

    wizard_id = fields.Many2one('l10n_ch.hr.payroll.employee.lang.wizard')
    employee_id = fields.Many2one('hr.employee')
    lang = fields.Selection(_lang_get, string="Language", required=True, default=lambda self: self._lang_get()[0][0])
