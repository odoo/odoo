#!/usr/bin/env python
#-*- coding:utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime
from report import report_sxw
from tools import amount_to_text_en

class payslip_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(payslip_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
                'convert': self.convert,
                'get_month': self.get_month,
                'get_earnings': self.get_earnings,
                'get_deductions':self.get_deductions,
                'get_leave': self.get_leave,
                'get_payslip_lines': self.get_payslip_lines,
                'get_details_by_rule_category': self.get_details_by_rule_category,
                'get_lines_by_contribution_register': self.get_lines_by_contribution_register,
        })

    def convert(self, amount, cur):
        amt_en = amount_to_text_en.amount_to_text(amount, 'en', cur)
        return amt_en

    def get_leave(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
#        ids = []
#        for id in range(len(obj)):
#            if obj[id].type == 'leaves':
#                ids.append(obj[id].id)
#        if ids:
#            res = payslip_line.browse(self.cr, self.uid, ids)
        return res

    def get_earnings(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
        ids = []
        for id in range(len(obj)):
            if obj[id].category_id.parent_id.name == 'Allowance':
                ids.append(obj[id].id)
        if ids:
            res = payslip_line.browse(self.cr, self.uid, ids)
        return res

    def get_deductions(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
        ids = []
        for id in range(len(obj)):
            if obj[id].category_id.parent_id.name == 'Deduction':
                ids.append(obj[id].id)
        if ids:
            res = payslip_line.browse(self.cr, self.uid, ids)
        return res

    def get_month(self, obj):
        res = {
                'mname':''
        }
        date = datetime.strptime(obj.date, '%Y-%m-%d')
        res['mname']= date.strftime('%B')+"-"+date.strftime('%Y')
        return res['mname']

    def get_payslip_lines(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
        ids = []
        for id in range(len(obj)):
            if obj[id].appears_on_payslip == True:
                ids.append(obj[id].id)
        if ids:
            res = payslip_line.browse(self.cr, self.uid, ids)
        return res

    def get_recursive_parent(self, rule_categories):
        if not rule_categories:
            return []
        if rule_categories[0].parent_id:
            rule_categories.insert(0, rule_categories[0].parent_id)
            self.get_recursive_parent(rule_categories)
        return rule_categories

    def get_details_by_rule_category(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        rule_cate_obj = self.pool.get('hr.salary.rule.category')
        res = []
        result = {}
        ids = []

        for id in range(len(obj)):
            ids.append(obj[id].id)
        if ids:
            self.cr.execute('''SELECT pl.id, pl.category_id FROM hr_payslip_line as pl \
                LEFT JOIN hr_salary_rule_category AS rc on (pl.category_id = rc.id) \
                WHERE pl.id in %s \
                GROUP BY rc.parent_id, pl.sequence, pl.id, pl.category_id \
                ORDER BY pl.sequence, rc.parent_id''',(tuple(ids),))
            for x in self.cr.fetchall():
                result.setdefault(x[1], [])
                result[x[1]].append(x[0])
            for key, value in result.iteritems():
                rule_categories = rule_cate_obj.browse(self.cr, self.uid, [key])
                parents = self.get_recursive_parent(rule_categories)
                category_total = 0
                for line in payslip_line.browse(self.cr, self.uid, value):
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
                for line in payslip_line.browse(self.cr, self.uid, value):
                    res.append({
                                'rule_category': line.name,
                                'name': line.name,
                                'code': line.code,
                                'total': line.total,
                                'level': level
                    })
        return res

    def get_lines_by_contribution_register(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        result = {}
        res = []

        for id in range(len(obj)):
            if obj[id].register_id:
                result.setdefault(obj[id].register_id.name, [])
                result[obj[id].register_id.name].append(obj[id].id)
        for key, value in result.iteritems():
            res.append({
                'register_name': key,
            })
            for line in payslip_line.browse(self.cr, self.uid, value):
                res.append({
                            'name': line.name,
                            'code': line.code,
                            'total': line.total,
                })
        return res

#report_sxw.report_sxw('report.payslip.pdf', 'hr.payslip', 'hr_payroll/report/payslip.rml', parser=payslip_report)
report_sxw.report_sxw('report.test.pdf', 'hr.payslip', 'hr_payroll/report/report_payslip.rml', parser=payslip_report)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: