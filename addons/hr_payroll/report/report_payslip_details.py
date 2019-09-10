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

from openerp.osv import osv
from openerp.report import report_sxw


class payslip_details_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(payslip_details_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_details_by_rule_category': self.get_details_by_rule_category,
            'get_lines_by_contribution_register': self.get_lines_by_contribution_register,
        })

    def get_details_by_rule_category(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        rule_cate_obj = self.pool.get('hr.salary.rule.category')

        def get_recursive_parent(current_rule_category, rule_categories = None):
            if rule_categories:
                rule_categories = current_rule_category | rule_categories
            else:
                rule_categories = current_rule_category

            if current_rule_category.parent_id:
                return get_recursive_parent(current_rule_category.parent_id, rule_categories)
            else:
                return rule_categories

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
                parents = get_recursive_parent(rule_categories)
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
            register_total = 0
            for line in payslip_line.browse(self.cr, self.uid, value):
                register_total += line.total
            res.append({
                'register_name': key,
                'total': register_total,
            })
            for line in payslip_line.browse(self.cr, self.uid, value):
                res.append({
                    'name': line.name,
                    'code': line.code,
                    'quantity': line.quantity,
                    'amount': line.amount,
                    'total': line.total,
                })
        return res


class wrapped_report_payslipdetails(osv.AbstractModel):
    _name = 'report.hr_payroll.report_payslipdetails'
    _inherit = 'report.abstract_report'
    _template = 'hr_payroll.report_payslipdetails'
    _wrapped_report_class = payslip_details_report

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
