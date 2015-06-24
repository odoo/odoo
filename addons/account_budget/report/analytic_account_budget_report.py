# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
from openerp.tools.misc import formatLang


class AnalyticAccountBudgetReport(models.AbstractModel):
    _name = 'report.account_budget.report_analyticaccountbudget'

    def funct(self, object, form):
        global tot
        tot = {
            'theo':0.00,
            'pln':0.00,
            'prac':0.00,
            'perc':0.00
        }
        result = []
        CrossoveredBudgetLines = self.env['crossovered.budget.lines']
        for account in object:
            res = {}
            budget_lines = account.crossovered_budget_line
            if not budget_lines:
                return []
            budgets = set([budget_id.crossovered_budget_id for budget_id in budget_lines])
            for budget in budgets:
                res = {
                    'b_id':'-1',
                    'a_id':'-1',
                    'name':budget.name,
                    'status':1,
                    'theo':0.00,
                    'pln':0.00,
                    'prac':0.00,
                    'perc':0.00
                }
                result.append(res)

                lines = CrossoveredBudgetLines.search([('id', 'in', budget_lines.ids), ('crossovered_budget_id', '=', budget.id)])
                tot_theo = tot_pln = tot_prac = tot_perc = 0

                done_budget = []
                for line in lines:
                    if line.id in budget_lines.ids:
                        theo = pract = 0.00
                        theo = line._theo_amt()[line.id]
                        pract = line._prac_amt()[line.id]
                        if line.general_budget_id.id in done_budget:
                            for record in result:
                                if record['b_id'] == line.general_budget_id.id and record['a_id'] == line.analytic_account_id.id:
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
                            res1 = {
                                'b_id':line.general_budget_id.id,
                                'a_id':line.analytic_account_id.id,
                                'name':line.general_budget_id.name,
                                'status':2,
                                'theo':0.00,
                                'pln':0.00,
                                'prac':0.00,
                                'perc':0.00
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

    @api.multi
    def render_html(self, data=None):
        Report = self.env['report']
        followup_report = Report._get_report_from_name('account_budget.report_analyticaccountbudget')
        selected_records = self.env['account.analytic.account'].browse(data['form']['ids'])
        docargs = {
            'doc_ids': self.ids,
            'doc_model': followup_report.model,
            'docs': selected_records,
            'funct': self.funct(selected_records, data['form']),
            'funct_total': self.funct_total(data['form']),
            'data': data,
            'formatLang': formatLang,
            'date': fields.Date
        }
        return Report.render('account_budget.report_analyticaccountbudget', docargs)
