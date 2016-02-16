# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class BudgetReport(models.AbstractModel):
    _name = 'report.account_budget.report_crossoveredbudget'

    def get_budget_lines(self, crossovered_budgets, form):
        result = {}
        for crossovered_budget in crossovered_budgets:
            budget_lines = crossovered_budget.crossovered_budget_line
            lines = []
            budget_total = {
                'tot_theo': 0.00,
                'tot_pln': 0.00,
                'tot_prac': 0.00,
                'tot_perc': 0.00
            }
            if not budget_lines:
                result.update({crossovered_budget.id: {'lines': lines, 'budget_total': budget_total}})
                continue
            for analytic_account in budget_lines.mapped('analytic_account_id'):
                lines.append({
                    'b_id': '-1',
                    'a_id': '-1',
                    'name': analytic_account.name,
                    'status': 1,
                    'theo': 0.00,
                    'pln': 0.00,
                    'prac': 0.00,
                    'perc': 0.00
                })
                tot_theo = tot_pln = tot_prac = tot_perc = 0.00
                done_budget = []
                for line in budget_lines.filtered(lambda rec: rec.analytic_account_id == analytic_account and rec.date_to >= form['date_from'] and rec.date_from <= form['date_to']):
                    theo = pract = 0.00
                    theo = line._theo_amt()[line.id]
                    pract = line._prac_amt()[line.id]
                    if line.general_budget_id.id in done_budget:
                        for record in lines:
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
                            lines.append(res1)
                            done_budget.append(line.general_budget_id.id)
                if tot_theo == 0.00:
                    tot_perc = 0.00
                else:
                    tot_perc = float(tot_prac / tot_theo) * 100
                if form['report'] == 'analytic-full':
                    lines[-(len(done_budget) + 1)]['theo'] = tot_theo
                    budget_total['tot_theo'] += tot_theo
                    lines[-(len(done_budget) + 1)]['pln'] = tot_pln
                    budget_total['tot_pln'] += tot_pln
                    lines[-(len(done_budget) + 1)]['prac'] = tot_prac
                    budget_total['tot_prac'] += tot_prac
                    lines[-(len(done_budget) + 1)]['perc'] = tot_perc
                else:
                    lines[-1]['theo'] = tot_theo
                    budget_total['tot_theo'] += tot_theo
                    lines[-1]['pln'] = tot_pln
                    budget_total['tot_pln'] += tot_pln
                    lines[-1]['prac'] = tot_prac
                    budget_total['tot_prac'] += tot_prac
                    lines[-1]['perc'] = tot_perc
            if budget_total['tot_theo'] == 0.00:
                budget_total['tot_perc'] = 0.00
            else:
                budget_total['tot_perc'] = float(budget_total['tot_prac'] / budget_total['tot_theo']) * 100
            result.update({crossovered_budget.id: {'lines': lines, 'budget_total': budget_total}})
        return result

    @api.multi
    def render_html(self, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids'))
        crossovered_budgets = self.env['crossovered.budget'].browse(data['form']['ids'])
        result = self.get_budget_lines(crossovered_budgets, data['form'])
        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
            'crossoveredbudgets': result,
            'date_from': data['form']['date_from'],
            'date_to': data['form']['date_to']
        }
        return self.env['report'].render('account_budget.report_crossoveredbudget', docargs)
