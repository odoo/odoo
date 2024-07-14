# -*- coding: utf-8 -*-

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSubscription(TestSubscriptionCommon):

    def test_report_multi_currency(self):
        sub_a = self.subscription.create({
            'name': 'Company1 - Currency1',
            'sale_order_template_id': self.subscription_tmpl.id,
            'partner_id': self.user_portal.partner_id.id,
            'currency_id': self.company.currency_id.id,
            'plan_id': self.plan_month.id,
            'order_line': [(0, 0, {
                'name': "Product 1",
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom': self.product.uom_id.id
            })]
        })
        sub_a.action_confirm()
        sub_b = self.subscription.create({
            'name': 'Company1 - Currency2',
            'partner_id': self.user_portal.partner_id.id,
            'plan_id': self.plan_month.id,
            'order_line': [(0, 0, {
                'name': "Product 1",
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom': self.product.uom_id.id
            })]
        })
        sub_b.write({
            'currency_id': self.currency_data['currency'].id,
        })
        self.currency_data['currency'].write({
            'rate_ids': [(0, 0, {
                'rate': 2,
            })]
        })
        sub_b.action_confirm()

        self.env.flush_all()

        report_a = self.env['sale.subscription.report'].search([('name', '=', 'Company1 - Currency1')])
        report_b = self.env['sale.subscription.report'].search([('name', '=', 'Company1 - Currency2')])
        self.assertEqual(len(report_a), 1, 'There should be on report for the given pair currency/company')
        self.assertEqual(len(report_b), 1, 'There should be on report for the given pair currency/company')
        self.assertAlmostEqual(report_a.recurring_total, report_b.recurring_total * 2, delta=0.01,
                         msg='Report B should have 2 time more recurring compared to A when converted in the same currency')
        self.assertAlmostEqual(report_a.recurring_monthly, report_b.recurring_monthly * 2, delta=0.01,
                         msg='Report B should have 2 time more recurring monthly compared to A when converted in the same currency')
        self.assertAlmostEqual(report_a.recurring_yearly, report_b.recurring_yearly *2, delta=0.1,
                         msg='Report B should have 2 time more recurring yearly compared to A when converted in the same currency')

    def test_report_multi_company(self):
        sub_a = self.subscription.create({
            'name': 'Company1 - Currency1 - Bis',
            'sale_order_template_id': self.subscription_tmpl.id,
            'partner_id': self.user_portal.partner_id.id,
            'currency_id': self.company.currency_id.id,
            'plan_id': self.plan_month.id,
            'order_line': [(0, 0, {
                'name': "Product 1",
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom': self.product.uom_id.id
            })]
        })
        sub_a.action_confirm()
        sub_b = self.subscription.create({
            'name': 'Company2 - Currency1 - Bis',
            'partner_id': self.user_portal.partner_id.id,
            'company_id': self.company_data_2['company'].id,
            'plan_id': self.plan_month.id,
            'order_line': [(0, 0, {
                'name': "Product 1",
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom': self.product.uom_id.id
            })]
        })
        sub_b.action_confirm()
        sub_c = self.subscription.create({
            'name': 'Company2 - Currency2 - Bis',
            'partner_id': self.user_portal.partner_id.id,
            'company_id': self.company_data_2['company'].id,
            'plan_id': self.plan_month.id,
            'order_line': [(0, 0, {
                'name': "Product 1",
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom': self.product.uom_id.id
            })]
        })
        sub_c.write({
            'currency_id': self.currency_data['currency'].id,
        })
        self.currency_data['currency'].write({
            'rate_ids': [(0, 0, {
                'rate': 2,
                'company_id': self.company_data_2['company'].id,
            })]
        })
        sub_c.action_confirm()

        self.env.flush_all()

        report_a = self.env['sale.subscription.report'].search([('name', '=', 'Company1 - Currency1 - Bis')])
        report_b = self.env['sale.subscription.report'].search([('name', '=', 'Company2 - Currency1 - Bis')])
        report_c = self.env['sale.subscription.report'].search([('name', '=', 'Company2 - Currency2 - Bis')])

        self.assertEqual(len(report_a), 1, 'There should be on report for the given pair currency/company')
        self.assertEqual(len(report_b), 1, 'There should be on report for the given pair currency/company')
        self.assertEqual(len(report_c), 1, 'There should be on report for the given pair currency/company')

        self.assertAlmostEqual(report_a.recurring_total, report_b.recurring_total, delta=0.01,
                               msg='Report B should have the same recurring compared to A when converted in the same currency')
        self.assertAlmostEqual(report_a.recurring_monthly, report_b.recurring_monthly, delta=0.01,
                               msg='Report B should have the same recurring monthly compared to A when converted in the same currency')
        self.assertAlmostEqual(report_a.recurring_yearly, report_b.recurring_yearly, delta=0.01,
                               msg='Report B should have the same recurring yearly compared to A when converted in the same currency')

        self.assertAlmostEqual(report_a.recurring_total, report_c.recurring_total * 2, delta=0.01,
                         msg='Report C should have 2 time more recurring compared to A when converted in the same currency')
        self.assertAlmostEqual(report_a.recurring_monthly, report_c.recurring_monthly * 2, delta=0.01,
                         msg='Report C should have 2 time more recurring monthly compared to A when converted in the same currency')
        self.assertAlmostEqual(report_a.recurring_yearly, report_c.recurring_yearly * 2, delta=0.1,
                         msg='Report C should have 2 time more recurring yearly compared to A when converted in the same currency')
