#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PayslipDetailsReport(models.AbstractModel):
    _name = 'report.hr_payroll.report_payslipdetails'

    def get_details_by_rule_category(self, payslip_lines):
        PayslipLine = self.env['hr.payslip.line']
        SalaryRuleCategory = self.env['hr.salary.rule.category']

        def get_recursive_parent(rule_categories):
            if not rule_categories:
                return []
            if rule_categories[0].parent_id:
                rule_categories = rule_categories[0].parent_id | rule_categories
                get_recursive_parent(rule_categories)
            return rule_categories

        res = []
        result = {}

        if payslip_lines.ids:
            self.env.cr.execute('''SELECT pl.id, pl.category_id FROM hr_payslip_line as pl \
                LEFT JOIN hr_salary_rule_category AS rc on (pl.category_id = rc.id) \
                WHERE pl.id in %s \
                GROUP BY rc.parent_id, pl.sequence, pl.id, pl.category_id \
                ORDER BY pl.sequence, rc.parent_id''', (tuple(payslip_lines.ids),))
            for x in self.env.cr.fetchall():
                result.setdefault(x[1], [])
                result[x[1]].append(x[0])
            for key, value in result.iteritems():
                rule_categories = SalaryRuleCategory.browse([key])
                parents = get_recursive_parent(rule_categories)
                category_total = 0
                for line in PayslipLine.browse(value):
                    category_total += line.total
                level = 0
                for parent in parents:
                    res.append({
                        'rule_category': parent.name,
                        'name': parent.name,
                        'code': parent.code,
                        'level': level,
                        'total': category_total,
                    })
                    level += 1
                for line in PayslipLine.browse(value):
                    res.append({
                        'rule_category': line.name,
                        'name': line.name,
                        'code': line.code,
                        'total': line.total,
                        'level': level
                    })
        return res

    def get_lines_by_contribution_register(self, payslip_lines):
        payslip_line = self.env['hr.payslip.line']
        result = {}
        res = []

        for line in payslip_lines.filtered(lambda x: x.register_id):
            result.setdefault(line.register_id.name, [])
            result[line.register_id.name].append(line.id)
        for key, value in result.iteritems():
            register_total = 0
            for line in payslip_line.browse(value):
                register_total += line.total
            res.append({
                'register_name': key,
                'total': register_total,
            })
            for line in payslip_line.browse(value):
                res.append({
                    'name': line.name,
                    'code': line.code,
                    'quantity': line.quantity,
                    'amount': line.amount,
                    'total': line.total,
                })
        return res

    @api.multi
    def render_html(self, data=None):
        Report = self.env['report']
        report = Report._get_report_from_name('hr_payroll.report_payslipdetails')
        payslip = self.env['hr.payslip'].browse(self.ids)
        docargs = {
            'doc_ids': self.ids,
            'doc_model': report.model,
            'docs': payslip,
            'data': data,
            'get_details_by_rule_category': self.get_details_by_rule_category(payslip.line_ids),
            'get_lines_by_contribution_register': self.get_lines_by_contribution_register(payslip.line_ids),
        }
        return Report.render('hr_payroll.report_payslipdetails', docargs)
