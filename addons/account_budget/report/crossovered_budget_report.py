# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CrossoveredBudgetReport(models.AbstractModel):
    
    _name = 'report.account_budget.report_crossoveredbudget'

    def funct(self, budget, form):
        global tot
        tot = {
            'theo':0.00,
            'pln':0.00,
            'prac':0.00,
            'perc':0.00
        }
        result = []
        res = {}
        d_from = form['date_from']
        d_to = form['date_to']
        
        budget_lines = budget.crossovered_budget_line
        if not budget_lines:
            return []
        
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
            result.append(res)
            tot_theo = tot_pln = tot_prac = tot_perc = 0.00

            done_budget = []
            for line in budget_lines.filtered(lambda rec: rec.analytic_account_id == analytic_account and rec.date_to >= form['date_from'] and rec.date_from <= form['date_to']):
                if line in budget_lines:
                    theo = pract = 0.00
                    theo = line.with_context(wizard_date_from=d_from, wizard_date_to=d_to)._theo_amt()[line.id]
                    pract = line.with_context(wizard_date_from=d_from, wizard_date_to=d_to)._prac_amt()[line.id]
                    if line.general_budget_id.id in done_budget:
                        for record in result:
                            if record['b_id'] == line.general_budget_id.id  and record['a_id'] == line.analytic_account_id.id:
                                record['theo'] += theo
                                record['pln'] += line.planned_amount
                                record['prac'] += pract
                                if record['theo'] <> 0.00:
                                    perc = (record['prac'] / record['theo']) * 100
                                else:
                                    perc = 0.00
                                record['perc'] = perc
                                tot_theo += theo
                                tot_pln += line.planned_amount
                                tot_prac += pract
                                tot_perc += perc
                    else:
                        if theo <> 0.00:
                            perc = (pract / theo) * 100
                        else:
                            perc = 0.00
                        res1 = {
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
                        res1 = {
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
                result[-(len(done_budget) + 1)]['theo'] = tot_theo
                tot['theo'] += tot_theo
                result[-(len(done_budget) + 1)]['pln'] = tot_pln
                tot['pln'] += tot_pln
                result[-(len(done_budget) + 1)]['prac'] = tot_prac
                tot['prac'] += tot_prac
                result[-(len(done_budget) + 1)]['perc'] = tot_perc
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
        res = {
            'tot_theo': tot['theo'],
            'tot_pln': tot['pln'],
            'tot_prac': tot['prac'],
            'tot_perc': tot['perc']
        }
        result.append(res)
        return result

    @api.multi
    def render_html(self, data):
        self.model = self.env.context.get('active_model')
        budgets = self.env['crossovered.budget'].browse(data['form']['ids'])
        
        lines = {}
        totals = {}
        for budget in budgets:
            lines[budget.id] = self.funct(budget, data['form'])
            totals[budget.id] = self.funct_total(data['form'])
        
        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': budgets,
            'funct': lines,
            'funct_total': totals,
            'data': data,
        }
        return self.env['report'].render('account_budget.report_crossoveredbudget', docargs)
