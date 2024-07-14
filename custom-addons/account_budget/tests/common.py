# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestAccountBudgetCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # ==== Analytic accounts ====

        cls.analytic_plan_projects = cls.env['account.analytic.plan'].create({'name': 'Projects'})
        cls.analytic_plan_departments = cls.env['account.analytic.plan'].create({'name': 'Departments test'})

        cls.analytic_account_partner_a_1 = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_partner_a_1',
            'partner_id': cls.partner_a.id,
            'plan_id': cls.analytic_plan_projects.id,
        })
        cls.analytic_account_partner_a_2 = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_partner_a_2',
            'partner_id': cls.partner_a.id,
            'plan_id': cls.analytic_plan_projects.id,
        })
        cls.analytic_account_partner_a_3 = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_partner_a_3',
            'partner_id': cls.partner_a.id,
            'plan_id': cls.analytic_plan_projects.id,
        })
        cls.analytic_account_partner_b = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_partner_b',
            'partner_id': cls.partner_b.id,
            'plan_id': cls.analytic_plan_projects.id,
        })
        cls.analytic_account_administratif = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_administratif',
            'plan_id': cls.analytic_plan_departments.id,
        })

        # ==== Crossovered Budget ====

        cls.crossovered_budget_budgetoptimistic0 = cls.env['crossovered.budget'].create({
            'name': 'Budget 2019: Optimistic',
            'date_from': '2019-01-01',
            'date_to': '2019-12-31',
            'state': 'draft',
            'user_id': cls.env.ref('base.user_admin').id,
            'crossovered_budget_line': [
                (0, 0, {
                    'date_from': '2019-01-01',
                    'date_to': '2019-12-31',
                    'planned_amount': -35000,
                    'analytic_account_id': cls.analytic_account_administratif.id,
                }), (0, 0, {
                    'date_from': '2019-01-01',
                    'date_to': '2019-01-31',
                    'planned_amount': 10000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-02-01',
                    'date_to': '2019-02-28',
                    'planned_amount': 10000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-03-01',
                    'date_to': '2019-03-31',
                    'planned_amount': 12000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-04-01',
                    'date_to': '2019-04-30',
                    'planned_amount': 15000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-05-01',
                    'date_to': '2019-05-31',
                    'planned_amount': 15000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-06-01',
                    'date_to': '2019-06-30',
                    'planned_amount': 15000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-07-01',
                    'date_to': '2019-07-31',
                    'planned_amount': 13000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-08-01',
                    'date_to': '2019-08-31',
                    'planned_amount': 9000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-09-01',
                    'date_to': '2019-09-30',
                    'planned_amount': 8000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-10-01',
                    'date_to': '2019-10-31',
                    'planned_amount': 15000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-11-01',
                    'date_to': '2019-11-30',
                    'planned_amount': 15000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-12-01',
                    'date_to': '2019-12-31',
                    'planned_amount': 18000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                })
            ]
        })

        cls.crossovered_budget_budgetpessimistic0 = cls.env['crossovered.budget'].create({
            'name': 'Budget 2019: Pessimistic',
            'date_from': '2019-01-01',
            'date_to': '2019-12-31',
            'state': 'draft',
            'user_id': cls.env.ref('base.user_admin').id,
            'crossovered_budget_line': [
                (0, 0, {
                    'date_from': '2019-01-01',
                    'date_to': '2019-12-31',
                    'planned_amount': -55000,
                    'analytic_account_id': cls.analytic_account_administratif.id,
                }), (0, 0, {
                    'date_from': '2019-01-01',
                    'date_to': '2019-01-31',
                    'planned_amount': 9000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-02-01',
                    'date_to': '2019-02-28',
                    'planned_amount': 8000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-03-01',
                    'date_to': '2019-03-31',
                    'planned_amount': 10000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-04-01',
                    'date_to': '2019-04-30',
                    'planned_amount': 14000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-05-01',
                    'date_to': '2019-05-31',
                    'planned_amount': 16000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-06-01',
                    'date_to': '2019-06-30',
                    'planned_amount': 13000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-07-01',
                    'date_to': '2019-07-31',
                    'planned_amount': 10000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-08-01',
                    'date_to': '2019-08-31',
                    'planned_amount': 8000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-09-01',
                    'date_to': '2019-09-30',
                    'planned_amount': 7000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-10-01',
                    'date_to': '2019-10-31',
                    'planned_amount': 12000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-11-01',
                    'date_to': '2019-11-30',
                    'planned_amount': 17000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                }), (0, 0, {
                    'date_from': '2019-12-01',
                    'date_to': '2019-12-31',
                    'planned_amount': 17000,
                    'analytic_account_id': cls.analytic_account_partner_a_1.id,
                })
            ]
        })

        # ==== Crossovered Budget Lines ====

        cls.account_budget_post_sales0 = cls.env['account.budget.post'].create({
            'name': 'Sales',
            'account_ids': [(6, None, cls.company_data['default_account_revenue'].ids)],
        })

        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_b.id,
            'general_budget_id': cls.account_budget_post_sales0.id,
            'date_from': '2019-01-01',
            'date_to': '2019-01-31',
            'planned_amount': 500.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_b.id,
            'general_budget_id': cls.account_budget_post_sales0.id,
            'date_from': '2019-02-07',
            'date_to': '2019-02-28',
            'planned_amount': 900.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_b.id,
            'general_budget_id': cls.account_budget_post_sales0.id,
            'date_from': '2019-03-01',
            'date_to': '2019-03-15',
            'planned_amount': 300.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_a_2.id,
            'general_budget_id': cls.account_budget_post_sales0.id,
            'date_from': '2019-03-16',
            'paid_date': '2019-12-03',
            'date_to': '2019-03-31',
            'planned_amount': 375.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_a_2.id,
            'general_budget_id': cls.account_budget_post_sales0.id,
            'date_from': '2019-05-01',
            'paid_date': '2019-12-03',
            'date_to': '2019-05-31',
            'planned_amount': 375.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_a_3.id,
            'general_budget_id': cls.account_budget_post_sales0.id,
            'date_from': '2019-07-16',
            'date_to': '2019-07-31',
            'planned_amount': 20000.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_a_3.id,
            'general_budget_id': cls.account_budget_post_sales0.id,
            'date_from': '2019-02-01',
            'date_to': '2019-02-28',
            'planned_amount': 20000.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_a_3.id,
            'general_budget_id': cls.account_budget_post_sales0.id,
            'date_from': '2019-09-16',
            'date_to': '2019-09-30',
            'planned_amount': 10000.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_a_3.id,
            'general_budget_id': cls.account_budget_post_sales0.id,
            'date_from': '2019-10-01',
            'date_to': '2019-12-31',
            'planned_amount': 10000.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })

        cls.account_budget_post_purchase0 = cls.env['account.budget.post'].create({
            'name': 'Purchases',
            'account_ids': [(6, None, cls.company_data['default_account_expense'].ids)],
        })

        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_b.id,
            'general_budget_id': cls.account_budget_post_purchase0.id,
            'date_from': '2019-01-01',
            'date_to': '2019-01-31',
            'planned_amount': -500.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_b.id,
            'general_budget_id': cls.account_budget_post_purchase0.id,
            'date_from': '2019-02-01',
            'date_to': '2019-02-28',
            'planned_amount': -250.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_a_2.id,
            'general_budget_id': cls.account_budget_post_purchase0.id,
            'date_from': '2019-04-01',
            'date_to': '2019-04-30',
            'planned_amount': -150.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_a_3.id,
            'general_budget_id': cls.account_budget_post_purchase0.id,
            'date_from': '2019-06-01',
            'date_to': '2019-06-15',
            'planned_amount': -7500.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_a_3.id,
            'general_budget_id': cls.account_budget_post_purchase0.id,
            'date_from': '2019-06-16',
            'date_to': '2019-06-30',
            'planned_amount': -5000.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_a_3.id,
            'general_budget_id': cls.account_budget_post_purchase0.id,
            'date_from': '2019-07-01',
            'date_to': '2019-07-15',
            'planned_amount': -2000.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_a_3.id,
            'general_budget_id': cls.account_budget_post_purchase0.id,
            'date_from': '2019-08-16',
            'date_to': '2019-08-31',
            'planned_amount': -3000.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
        cls.env['crossovered.budget.lines'].create({
            'analytic_account_id': cls.analytic_account_partner_a_3.id,
            'general_budget_id': cls.account_budget_post_purchase0.id,
            'date_from': '2019-09-01',
            'date_to': '2019-09-15',
            'planned_amount': -1000.0,
            'crossovered_budget_id': cls.crossovered_budget_budgetpessimistic0.id,
        })
