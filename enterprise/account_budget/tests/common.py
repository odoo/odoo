# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.fields import Command


class TestAccountBudgetCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ==== Products ====
        cls.product_a = cls.env['product.product'].create({
            'name': 'product_a',
            'standard_price': 100.0,
            'supplier_taxes_id': False
        })
        cls.product_b = cls.env['product.product'].create({
            'name': 'product_b',
            'standard_price': 100.0,
            'supplier_taxes_id': False
        })

        # ==== Analytic accounts ====

        cls.analytic_plan_projects = cls.env['account.analytic.plan'].create({'name': 'Projects'})
        cls.analytic_plan_departments = cls.env['account.analytic.plan'].create({'name': 'Departments test'})

        cls.project_column_name = cls.analytic_plan_projects._column_name()
        cls.department_column_name = cls.analytic_plan_departments._column_name()

        cls.analytic_account_partner_a = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_partner_a',
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
        cls.analytic_account_administratif_2 = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_administratif_2',
            'plan_id': cls.analytic_plan_departments.id,
        })

        # ==== Budget Analytic ====

        cls.budget_analytic_revenue = cls.env['budget.analytic'].create({
            'name': 'Budget 2019: Revenue',
            'date_from': '2019-01-01',
            'date_to': '2019-12-31',
            'budget_type': 'revenue',
            'state': 'draft',
            'user_id': cls.env.ref('base.user_admin').id,
            'budget_line_ids': [
                Command.create({
                    'budget_amount': 35000,
                    cls.project_column_name: cls.analytic_account_partner_a.id,
                }),
                Command.create({
                    'budget_amount': 10000,
                    cls.project_column_name: cls.analytic_account_partner_b.id,
                }),
                Command.create({
                    cls.project_column_name: cls.analytic_account_partner_b.id,
                    cls.department_column_name: cls.analytic_account_administratif.id,
                    'budget_amount': 10000.0,
                }),
            ]
        })

        cls.budget_analytic_expense = cls.env['budget.analytic'].create({
            'name': 'Budget 2019: Expense',
            'date_from': '2019-01-01',
            'date_to': '2019-12-31',
            'budget_type': 'expense',
            'state': 'draft',
            'user_id': cls.env.ref('base.user_admin').id,
            'budget_line_ids': [
                Command.create({
                    'budget_amount': 55000,
                    cls.project_column_name: cls.analytic_account_partner_a.id,
                }),
                Command.create({
                    'budget_amount': 9000,
                    cls.project_column_name: cls.analytic_account_partner_b.id,
                }),
                Command.create({
                    cls.project_column_name: cls.analytic_account_partner_b.id,
                    cls.department_column_name: cls.analytic_account_administratif.id,
                    'budget_amount': 10000.0,
                }),
            ]
        })

        cls.budget_analytic_both = cls.env['budget.analytic'].create({
            'name': 'Budget 2019: Both',
            'date_from': '2019-01-01',
            'date_to': '2019-12-31',
            'budget_type': 'both',
            'state': 'draft',
            'user_id': cls.env.ref('base.user_admin').id,
            'budget_line_ids': [
                Command.create({
                    'budget_amount': 20000,
                    cls.project_column_name: cls.analytic_account_partner_a.id,
                }),
                Command.create({
                    'budget_amount': 5000,
                    cls.project_column_name: cls.analytic_account_partner_b.id,
                }),
                Command.create({
                    cls.project_column_name: cls.analytic_account_partner_b.id,
                    cls.department_column_name: cls.analytic_account_administratif.id,
                    'budget_amount': 10000.0,
                }),
            ]
        })

        # ==== Purchase Order ====

        purchase_order = cls.env['purchase.order'].create({
            'partner_id': cls.partner_a.id,
            'date_order': '2019-01-10',
            'order_line': [
                Command.create({
                    'product_id': cls.product_a.id,
                    'product_qty': 10,
                    'analytic_distribution': {cls.analytic_account_partner_a.id: 100},
                }),
                Command.create({
                    'product_id': cls.product_a.id,
                    'product_qty': 10,
                    'analytic_distribution': {"%s,%s" % (cls.analytic_account_partner_a.id, cls.analytic_account_administratif.id): 100},
                }),
                Command.create({
                    'product_id': cls.product_b.id,
                    'product_qty': 10,
                    'analytic_distribution': {cls.analytic_account_partner_b.id: 100},
                }),
                Command.create({
                    'product_id': cls.product_b.id,
                    'product_qty': 10,
                    'analytic_distribution': {"%s,%s" % (cls.analytic_account_partner_b.id, cls.analytic_account_administratif.id): 100},
                }),
            ]
        })
        purchase_order.order_line._compute_analytic_json()
        purchase_order.button_confirm()
        purchase_order.write({
            'order_line': [
                Command.update(purchase_order.order_line.sorted()[0].id, {'qty_received': 1}),
                Command.update(purchase_order.order_line.sorted()[1].id, {'qty_received': 3}),
                Command.update(purchase_order.order_line.sorted()[2].id, {'qty_received': 6}),
                Command.update(purchase_order.order_line.sorted()[3].id, {'qty_received': 5}),
            ]
        })
        purchase_order.action_create_invoice()
        purchase_order.invoice_ids.write({'invoice_date': '2019-01-10'})
        cls.purchase_order = purchase_order

        account = cls.company_data['default_account_revenue']
        cls.out_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2019-01-10',
            'invoice_line_ids': [
                Command.create({
                    'product_id': cls.product_a.id,
                    'analytic_distribution': {cls.analytic_account_partner_a.id: 100},
                    'quantity': 2,
                    'price_unit': 100,
                    'account_id': account.id,
                }),
                Command.create({
                    'product_id': cls.product_a.id,
                    'analytic_distribution': {"%s,%s" % (cls.analytic_account_partner_a.id, cls.analytic_account_administratif.id): 100},
                    'quantity': 4,
                    'price_unit': 100,
                    'account_id': account.id,
                }),
                Command.create({
                    'product_id': cls.product_b.id,
                    'analytic_distribution': {cls.analytic_account_partner_b.id: 100},
                    'quantity': 7,
                    'price_unit': 100,
                    'account_id': account.id,
                }),
                Command.create({
                    'product_id': cls.product_b.id,
                    'analytic_distribution': {"%s,%s" % (cls.analytic_account_partner_b.id, cls.analytic_account_administratif.id): 100},
                    'quantity': 6,
                    'price_unit': 100,
                    'account_id': account.id,
                }),
            ]
        })

    def assertBudgetLine(self, budget_line, *, committed, achieved):
        budget_line.invalidate_recordset(['achieved_amount', 'committed_amount'])
        self.assertRecordValues(budget_line, [{'committed_amount': committed, 'achieved_amount': achieved}])
