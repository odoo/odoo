# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from openerp import api, fields, models
from openerp.tools.misc import formatLang

tot = {}


class BudgetReport(models.AbstractModel):
    _name = 'report.account_budget.report_budget'

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
        for budget_id in object:
            res = {}

            budget_ids = budget_id.crossovered_budget_line
            if not budget_ids:
                return []
            analytic_accounts = set([budget_id.analytic_account_id for budget_id in budget_ids])

            for analytic_account in analytic_accounts:
                res = {
                    'b_id': '-1',
                    'a_id': '-1',
                    'name': analytic_account.name,
                    'status': 1,
                    'theo': 0.00,
                    'pln': 0.00,
                    'prac': 0.00,
                    'perc': 0.00
                }
                result.append(res)

                lines = CrossoveredBudgetLines.search([('id', 'in', budget_ids.ids), ('analytic_account_id', '=', analytic_account.id)])
                tot_theo = tot_pln = tot_prac = tot_perc = 0.00

                done_budget = []
                for line in lines:
                    if line.id in budget_ids.ids:
                        theo = pract = 0.00
                        theo = line._theo_amt()[line.id]
                        pract = line._prac_amt()[line.id]
                        if line.general_budget_id.id in done_budget:
                            for record in result:
                                if record['b_id'] == line.general_budget_id.id and record['a_id'] == line.analytic_account_id.id:
                                    record['theo'] += theo
                                    record['pln'] += line.planned_amount
                                    record['prac'] += pract
                                    if record['theo'] != 0.00:
                                        perc = (record['prac'] / record['theo']) * 100
                                    else:
                                        perc = 0.00
                                    record['perc'] = perc
                                    tot_theo += theo
                                    tot_pln += line.planned_amount
                                    tot_prac += pract
                                    tot_perc += perc
                        else:
                            if theo != 0.00:
                                perc = (pract / theo) * 100
                            else:
                                perc = 0.00
                            res1={
                                    'a_id': line.analytic_account_id.id,
                                    'b_id': line.general_budget_id.id,
                                    'name': line.general_budget_id.name,
                                    'status': 2,
                                    'theo': theo,
                                    'pln': line.planned_amount,
                                    'prac': pract,
                                    'perc': perc,
                            }
                            tot_theo += theo
                            tot_pln += line.planned_amount
                            tot_prac += pract
                            tot_perc += perc
                            if form['report'] == 'analytic-full':
                                result.append(res1)
                                done_budget.append(line.general_budget_id.id)
                    else:

                        if line.general_budget_id.id in done_budget:
                            continue
                        else:
                            res1={
                                    'a_id': line.analytic_account_id.id,
                                    'b_id': line.general_budget_id.id,
                                    'name': line.general_budget_id.name,
                                    'status': 2,
                                    'theo': 0.00,
                                    'pln': 0.00,
                                    'prac': 0.00,
                                    'perc': 0.00
                            }
                            if form['report'] == 'analytic-full':
                                result.append(res1)
                                done_budget.append(line.general_budget_id.id)
                if tot_theo == 0.00:
                    tot_perc = 0.00
                else:
                    tot_perc = float(tot_prac / tot_theo) * 100
                if form['report'] == 'analytic-full':
                    result[-(len(done_budget) +1)]['theo'] = tot_theo
                    tot['theo'] +=tot_theo
                    result[-(len(done_budget) +1)]['pln'] = tot_pln
                    tot['pln'] +=tot_pln
                    result[-(len(done_budget) +1)]['prac'] = tot_prac
                    tot['prac'] +=tot_prac
                    result[-(len(done_budget) +1)]['perc'] = tot_perc
                else:
                    result[-1]['theo'] = tot_theo
                    tot['theo'] += tot_theo
                    result[-1]['pln'] = tot_pln
                    tot['pln'] += tot_pln
                    result[-1]['prac'] = tot_prac
                    tot['prac'] += tot_prac
                    result[-1]['perc'] = tot_perc
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
        followup_report = Report._get_report_from_name('account_budget.report_budget')
        selected_records = self.env['account.budget.post'].browse(data['form']['ids'])
        docargs = {
            'doc_ids': self.ids,
            'doc_model': followup_report.model,
            'docs': selected_records,
            'funct': self.funct(selected_records, data['form']),
            'funct_total': self.funct_total(data['form']),
            'data': data,
            'formatLang': formatLang,
            'date': fields.Date,
            'time': time,
        }
        return Report.render('account_budget.report_budget', docargs)
