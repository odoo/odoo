# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from openerp.osv import osv
from openerp.report import report_sxw


class analytic_account_budget_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(analytic_account_budget_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'funct': self.funct,
            'funct_total': self.funct_total,
            'time': time,
        })
        self.context = context

    def funct(self, object, form, ids=None, done=None, level=1):
        if ids is None:
            ids = {}
        if not ids:
            ids = self.ids
        if not done:
            done = {}

        global tot
        tot = {
            'theo':0.00,
            'pln':0.00,
            'prac':0.00,
            'perc':0.00
        }
        result = []
        accounts = self.pool.get('account.analytic.account').browse(self.cr, self.uid, [object.id], self.context.copy())
        c_b_lines_obj = self.pool.get('crossovered.budget.lines')
        obj_c_budget = self.pool.get('crossovered.budget')

        for account_id in accounts:
            res = {}
            b_line_ids = []
            for line in account_id.crossovered_budget_line:
                b_line_ids.append(line.id)
            if not b_line_ids:
                return []
            d_from = form['date_from']
            d_to = form['date_to']

            self.cr.execute('SELECT DISTINCT(crossovered_budget_id) FROM crossovered_budget_lines WHERE id =ANY(%s)',(b_line_ids,))
            budget_ids = self.cr.fetchall()

            context = {'wizard_date_from':d_from,'wizard_date_to':d_to}
            for i in range(0, len(budget_ids)):
                budget_name = obj_c_budget.browse(self.cr, self.uid, [budget_ids[i][0]])
                res= {
                     'b_id':'-1',
                     'a_id':'-1',
                     'name':budget_name[0].name,
                     'status':1,
                     'theo':0.00,
                     'pln':0.00,
                     'prac':0.00,
                     'perc':0.00
                }
                result.append(res)

                line_ids = c_b_lines_obj.search(self.cr, self.uid, [('id', 'in', b_line_ids), ('crossovered_budget_id','=',budget_ids[i][0])])
                line_id = c_b_lines_obj.browse(self.cr, self.uid, line_ids)
                tot_theo = tot_pln = tot_prac = tot_perc = 0

                done_budget = []
                for line in line_id:
                    if line.id in b_line_ids:
                        theo = pract = 0.00
                        theo = c_b_lines_obj._theo_amt(self.cr, self.uid, [line.id], context)[line.id]
                        pract = c_b_lines_obj._prac_amt(self.cr, self.uid, [line.id], context)[line.id]
                        if line.general_budget_id.id in done_budget:
                            for record in result:
                               if record['b_id'] == line.general_budget_id.id  and record['a_id'] == line.analytic_account_id.id:
                                    record['theo'] += theo
                                    record['pln'] += line.planned_amount
                                    record['prac'] += pract
                                    record['perc'] += line.percentage
                                    tot_theo += theo
                                    tot_pln += line.planned_amount
                                    tot_prac += pract
                                    tot_perc += line.percentage
                        else:
                            res1 = {
                                 'b_id': line.general_budget_id.id,
                                 'a_id': line.analytic_account_id.id,
                                 'name': line.general_budget_id.name,
                                 'status': 2,
                                 'theo': theo,
                                 'pln': line.planned_amount,
                                 'prac': pract,
                                 'perc': line.percentage
                            }
                            tot_theo += theo
                            tot_pln += line.planned_amount
                            tot_prac += pract
                            tot_perc += line.percentage
                            result.append(res1)
                            done_budget.append(line.general_budget_id.id)
                    else:
                       if line.general_budget_id.id in done_budget:
                            continue
                       else:
                            res1={
                                    'b_id': line.general_budget_id.id,
                                    'a_id': line.analytic_account_id.id,
                                     'name': line.general_budget_id.name,
                                     'status': 2,
                                     'theo': 0.00,
                                     'pln': 0.00,
                                     'prac': 0.00,
                                     'perc': 0.00
                            }
                            result.append(res1)
                            done_budget.append(line.general_budget_id.id)
                if tot_theo == 0.00:
                    tot_perc = 0.00
                else:
                    tot_perc = float(tot_prac / tot_theo) * 100

                result[-(len(done_budget) +1)]['theo'] = tot_theo
                tot['theo'] +=tot_theo
                result[-(len(done_budget) +1)]['pln'] = tot_pln
                tot['pln'] +=tot_pln
                result[-(len(done_budget) +1)]['prac'] = tot_prac
                tot['prac'] +=tot_prac
                result[-(len(done_budget) +1)]['perc'] = tot_perc
            if tot['theo'] == 0.00:
                tot['perc'] = 0.00
            else:
                tot['perc'] = float(tot['prac'] / tot['theo']) * 100
        return result

    def funct_total(self, form):
        result = []
        res = {}
        res = {
             'tot_theo': tot['theo'],
             'tot_pln': tot['pln'],
             'tot_prac': tot['prac'],
             'tot_perc': tot['perc']
        }
        result.append(res)
        return result


class report_analyticaccountbudget(osv.AbstractModel):
    _name = 'report.account_budget.report_analyticaccountbudget'
    _inherit = 'report.abstract_report'
    _template = 'account_budget.report_analyticaccountbudget'
    _wrapped_report_class = analytic_account_budget_report
