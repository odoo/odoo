#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ContributionRegisterReport(models.AbstractModel):
    _name = 'report.hr_payroll.contribution_register'
    _description = 'Model for Printing hr.payslip.line grouped by register'

    def _get_report_values(self, docids, data):
        docs = []
        lines_data = {}
        lines_total = {}

        for partner, total_sum, records in self.env['hr.payslip.line']._read_group([('id', 'in', docids), ('partner_id', '!=', False)], ['partner_id'], ['total:sum', 'id:recordset']):
            docid = partner.id
            docs.append(docid)
            lines_data[docid] = records
            lines_total[docid] = total_sum

        return {
            'docs': self.env['res.partner'].browse(docs),
            'data': data,
            'lines_data': lines_data,
            'lines_total': lines_total
        }
