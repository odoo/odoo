# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class FichePayeParser(models.AbstractModel):
    _name = 'report.l10n_fr_hr_payroll.report_l10n_fr_fiche_paye'
    _description = "French Pay Slip"

    def get_total_by_rule_category(self, obj, code):
        category_total = 0
        category_id = self.env['hr.salary.rule.category'].search([('code', '=', code)], limit=1).id
        if category_id:
            line_ids = self.env['hr.payslip.line'].search([('slip_id', '=', obj.id), ('category_id', 'child_of', category_id)])
            for line in line_ids:
                category_total += line.total
        return category_total

    def _get_employer_line(self, line):
        code = line.code or ''
        return line.slip_id.line_ids.filtered(lambda line: line.code == '%sP' % code)

    @api.model
    def _get_report_values(self, docids, data=None):
        payslip = self.env['hr.payslip'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'data': data,
            'docs': payslip,
            'lang': "fr_FR",
            'get_total_by_rule_category': self.get_total_by_rule_category,
            'get_employer_line': self._get_employer_line,
        }
