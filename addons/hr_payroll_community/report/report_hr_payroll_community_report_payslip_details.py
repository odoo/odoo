# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, models


class ReportHrPayrollCommunityReportPayslipDetails(models.AbstractModel):
    """Create new model for getting Payslip Details Report"""
    _name = 'report.hr_payroll_community.report_payslipdetails'
    _description = 'Payslip Details Report'

    def get_details_by_rule_category(self, payslip_lines):
        """Function for get Salary Rule Categories"""
        PayslipLine = self.env['hr.payslip.line']
        RuleCateg = self.env['hr.salary.rule.category']

        def get_recursive_parent(current_rule_category, rule_categories=None):
            """Function for return Rule Categories with respect to Parent
            Category"""
            if rule_categories:
                rule_categories = current_rule_category | rule_categories
            else:
                rule_categories = current_rule_category
            if current_rule_category.parent_id:
                return get_recursive_parent(current_rule_category.parent_id,
                                            rule_categories)
            else:
                return rule_categories
        res = {}
        result = {}
        if payslip_lines:
            self.env.cr.execute("""
                SELECT pl.id, pl.category_id, pl.slip_id FROM 
                hr_payslip_line as pl
                LEFT JOIN hr_salary_rule_category AS rc on 
                (pl.category_id = rc.id)
                WHERE pl.id in %s
                GROUP BY rc.parent_id, pl.sequence, pl.id, pl.category_id
                ORDER BY pl.sequence, rc.parent_id""",
                                (tuple(payslip_lines.ids),))
            for x in self.env.cr.fetchall():
                result.setdefault(x[2], {})
                result[x[2]].setdefault(x[1], [])
                result[x[2]][x[1]].append(x[0])
            for payslip_id, lines_dict in result.items():
                res.setdefault(payslip_id, [])
                for rule_categ_id, line_ids in lines_dict.items():
                    rule_categories = RuleCateg.browse(rule_categ_id)
                    lines = PayslipLine.browse(line_ids)
                    level = 0
                    for parent in get_recursive_parent(rule_categories):
                        res[payslip_id].append({
                            'rule_category': parent.name,
                            'name': parent.name,
                            'code': parent.code,
                            'level': level,
                            'total': sum(lines.mapped('total')),
                        })
                        level += 1
                    for line in lines:
                        res[payslip_id].append({
                            'rule_category': line.name,
                            'name': line.name,
                            'code': line.code,
                            'total': line.total,
                            'level': level
                        })
        return res

    def get_lines_by_contribution_register(self, payslip_lines):
        """Function for getting Contribution Register Lines"""
        result = {}
        res = {}
        for line in payslip_lines.filtered('register_id'):
            result.setdefault(line.slip_id.id, {})
            result[line.slip_id.id].setdefault(line.register_id, line)
            result[line.slip_id.id][line.register_id] |= line
        for payslip_id, lines_dict in result.items():
            res.setdefault(payslip_id, [])
            for register, lines in lines_dict.items():
                res[payslip_id].append({
                    'register_name': register.name,
                    'total': sum(lines.mapped('total')),
                })
                for line in lines:
                    res[payslip_id].append({
                        'name': line.name,
                        'code': line.code,
                        'quantity': line.quantity,
                        'amount': line.amount,
                        'total': line.total,
                    })
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        """Function for getting Payslip Details Report values"""
        payslips = self.env['hr.payslip'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'docs': payslips,
            'data': data,
            'get_details_by_rule_category': self.get_details_by_rule_category(
                payslips.mapped('details_by_salary_rule_category_ids').filtered(
                    lambda r: r.appears_on_payslip)),
            'get_lines_by_contribution_register':
                self.get_lines_by_contribution_register(
                payslips.mapped('line_ids').filtered(
                    lambda r: r.appears_on_payslip)),
        }
