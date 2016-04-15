# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models


class BudgetReport(models.AbstractModel):
    
    _name = 'report.account_budget.report_budget'

    def _get_budget_lines(self, budgets, form):
        AcccountBudgetPost = self.env['account.budget.post']
        result = {}
        
        for budget in budgets:
            lines = []
            res = {}
            budget_total = {
                'theo':0.00,
                'pln':0.00,
                'prac':0.00,
                'perc':0.00
            }

            date_from = form['date_from']
            date_to = form['date_to']
            
            budget_lines = budget.crossovered_budget_line
            if not budget_lines:
                result[budget.id] = {
                    'lines': lines, 
                    'budget_total': budget_total
                }
                continue
    
            for analytic_account in budget_lines.mapped('analytic_account_id'):
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
                lines.append(res)
                tot_theo = tot_pln = tot_prac = tot_perc = 0.00
    
                done_budget = AcccountBudgetPost.browse()
                for line in budget_lines.filtered(lambda rec: rec.analytic_account_id == analytic_account):
                    theo = pract = 0.00
                    theo = line.with_context(wizard_date_from=date_from, wizard_date_to=date_to)._theo_amt()[line.id]
                    pract = line.with_context(wizard_date_from=date_from, wizard_date_to=date_to)._prac_amt()[line.id]
                    if line.general_budget_id in done_budget:
                        for record in lines:
                            if record['b_id'] == line.general_budget_id.id  and record['a_id'] == line.analytic_account_id.id:
                                record['theo'] += theo
                                record['pln'] += line.planned_amount
                                record['prac'] += pract
                                perc = (record['prac'] / record['theo']) * 100 if record['theo'] <> 0.00 else 0.00 
                                record['perc'] = perc
                                tot_theo += theo
                                tot_pln += line.planned_amount
                                tot_prac += pract
                                tot_perc += perc
                    else:
                        perc = (pract / theo) * 100 if theo <> 0.00 else 0.00
                        tot_theo += theo
                        tot_pln += line.planned_amount
                        tot_prac += pract
                        tot_perc += perc
                        if form['report'] == 'analytic-full':
                            lines.append({
                                'a_id': line.analytic_account_id.id,
                                'b_id': line.general_budget_id.id,
                                'name': line.general_budget_id.name,
                                'status': 2,
                                'theo': theo,
                                'pln': line.planned_amount,
                                'prac': pract,
                                'perc': perc,
                            })
                            done_budget |= line.general_budget_id
                tot_perc = float(tot_prac / tot_theo) * 100 if tot_theo <> 0.00 else 0.00
                if form['report'] == 'analytic-full':
                    lines[-(len(done_budget) + 1)]['theo'] = tot_theo
                    budget_total['theo'] += tot_theo
                    lines[-(len(done_budget) + 1)]['pln'] = tot_pln
                    budget_total['pln'] += tot_pln
                    lines[-(len(done_budget) + 1)]['prac'] = tot_prac
                    budget_total['prac'] += tot_prac
                    lines[-(len(done_budget) + 1)]['perc'] = tot_perc
                else:
                    lines[-1]['theo'] = tot_theo
                    budget_total['theo'] += tot_theo
                    lines[-1]['pln'] = tot_pln
                    budget_total['pln'] += tot_pln
                    lines[-1]['prac'] = tot_prac
                    budget_total['prac'] += tot_prac
                    lines[-1]['perc'] = tot_perc
            budget_total['perc'] = float(budget_total['prac'] / budget_total['theo']) * 100 if budget_total['theo'] <> 0.00 else 0.00
            
            result[budget.id] = {
                'lines': lines, 
                'budget_total': budget_total
            }
        return result

    @api.multi
    def render_html(self, data):
        self.model = self.env.context.get('active_model')
        budgets = self.env[self.model].browse(data['form']['ids'])
        result = self._get_budget_lines(budgets, data['form'])
        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': budgets,
            'data': data,
            'time': time,
            'budgets': result,
            'date_from': data['form']['date_from'],
            'date_to': data['form']['date_to']
        }
        return self.env['report'].render('account_budget.report_budget', docargs)
