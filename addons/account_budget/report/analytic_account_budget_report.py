# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AnalyticAccountBudgetReport(models.AbstractModel):
    _name = 'report.account_budget.report_analyticaccountbudget'

    def get_budget_lines(self, analytic_accounts):
        result = {}
        for account in analytic_accounts:
            lines = []
            budget_total = {
                'tot_theo': 0.00,
                'tot_pln': 0.00,
                'tot_prac': 0.00,
                'tot_perc': 0.00
            }
            budget_lines = account.crossovered_budget_line
            if not budget_lines:
                result.update({account.id: {'lines': lines, 'budget_total': budget_total}})
                continue
            for crossovered_budget in budget_lines.mapped('crossovered_budget_id'):
                lines.append({
                    'b_id': '-1',
                    'a_id': '-1',
                    'name': crossovered_budget.name,
                    'status': 1,
                    'theo': 0.00,
                    'pln': 0.00,
                    'prac': 0.00,
                    'perc': 0.00
                })
                tot_theo = tot_pln = tot_prac = tot_perc = 0
                done_budget = []
                for line in budget_lines.filtered(lambda rec: rec.crossovered_budget_id == crossovered_budget):
                    theo = pract = 0.00
                    theo = line._theo_amt()[line.id]
                    pract = line._prac_amt()[line.id]
                    if line.general_budget_id.id in done_budget:
                        for record in lines:
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
                        lines.append({
                            'b_id': line.general_budget_id.id,
                            'a_id': line.analytic_account_id.id,
                            'name': line.general_budget_id.name,
                            'status': 2,
                            'theo': theo,
                            'pln': line.planned_amount,
                            'prac': pract,
                            'perc': line.percentage
                        })
                        tot_theo += theo
                        tot_pln += line.planned_amount
                        tot_prac += pract
                        tot_perc += line.percentage
                        done_budget.append(line.general_budget_id.id)
                if tot_theo == 0.00:
                    tot_perc = 0.00
                else:
                    tot_perc = float(tot_prac / tot_theo) * 100

                lines[-(len(done_budget) + 1)]['theo'] = tot_theo
                budget_total['tot_theo'] += tot_theo
                lines[-(len(done_budget) + 1)]['pln'] = tot_pln
                budget_total['tot_pln'] += tot_pln
                lines[-(len(done_budget) + 1)]['prac'] = tot_prac
                budget_total['tot_prac'] += tot_prac
                lines[-(len(done_budget) + 1)]['perc'] = tot_perc
            if budget_total['tot_theo'] == 0.00:
                budget_total['tot_perc'] = 0.00
            else:
                budget_total['tot_perc'] = float(budget_total['tot_prac'] / budget_total['tot_theo']) * 100
            result.update({account.id: {'lines': lines, 'budget_total': budget_total}})
        return result

    @api.multi
    def render_html(self, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids'))
        analytic_accounts = self.env['account.analytic.account'].browse(data['form']['ids'])
        result = self.get_budget_lines(analytic_accounts)
        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
            'account_budgets': result,
            'date_from': data['form']['date_from'],
            'date_to': data['form']['date_to']
        }
        return self.env['report'].render('account_budget.report_analyticaccountbudget', docargs)
