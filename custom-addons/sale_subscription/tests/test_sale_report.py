# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo import Command

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.tests import tagged

@tagged('-at_install', 'post_install')
class TestSaleReport(TestSubscriptionCommon):

    def setUp(self):
        super().setUp()
        self.recurring_product_tmp, self.no_recurring_product_tmpl = self.env['product.template'].create([
            {
                'name': 'Product A',
                'type': 'service',
                'list_price': 100,
                'taxes_id': [Command.set(self.tax_10.ids)],
                'recurring_invoice': True,
                'uom_id': self.env.ref('uom.product_uom_unit').id,
                'product_subscription_pricing_ids': [Command.set(self.pricing_month.ids)]
            },
            {
                'name': 'Product B',
                'type': 'consu',
                'list_price': 100,
                'taxes_id': [Command.set(self.tax_10.ids)],
                'recurring_invoice': False,
                'uom_id': self.env.ref('uom.product_uom_unit').id,
            }
        ])
        self.recurring_product, self.no_recurring_product = (self.recurring_product_tmp | self.no_recurring_product_tmpl).product_variant_id
        self.original_subscription = self.env['sale.order'].create({
                'name': 'Test subscription',
                'is_subscription': True,
                'note': "Subscription description",
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'plan_id': self.plan_month.id,
                'order_line': [Command.create({
                    'name': self.recurring_product.name,
                    'product_id': self.recurring_product.id,
                    'product_uom_qty': 2.0,
                    'product_uom': self.recurring_product.uom_id.id,
                    'price_unit': self.recurring_product.list_price,
                })]
            })
        self.original_subscription.action_confirm()
        self.env['sale.order']._cron_recurring_create_invoice()

    def test_report_no_confirm_upsell(self):
        action = self.original_subscription.prepare_upsell_order()
        upsell_sub = self.env['sale.order'].browse(action['res_id'])
        self.env.flush_all()

        report_lines = self.env['sale.report'].search([('name', 'in', [self.original_subscription.name, upsell_sub.name])])
        self.assertEqual(len(report_lines), 1)
        self.assertEqual(report_lines.product_id, self.recurring_product)
        self.assertEqual(report_lines.product_uom_qty, 2)

    def test_report_confirm_upsell(self):
        action = self.original_subscription.prepare_upsell_order()
        upsell_sub = self.env['sale.order'].browse(action['res_id'])
        upsell_sub.action_confirm()
        self.env.flush_all()

        report_lines = self.env['sale.report'].search([('name', 'in', [self.original_subscription.name, upsell_sub.name])])
        self.assertEqual(len(report_lines), 1)
        self.assertEqual(report_lines.product_id, self.recurring_product)
        self.assertEqual(report_lines.product_uom_qty, 2)

    def test_report_confirm_upsell_with_same_product(self):
        action = self.original_subscription.prepare_upsell_order()
        upsell_sub = self.env['sale.order'].browse(action['res_id'])
        upsell_sub.order_line = [Command.create({
                'name': self.recurring_product.name,
                'product_id': self.recurring_product.id,
                'product_uom_qty': 1.0,
                'price_unit': self.recurring_product.list_price,
            })]
        upsell_sub.action_confirm()
        self.env.flush_all()

        report_lines = self.env['sale.report'].search([('name', 'in', [self.original_subscription.name, upsell_sub.name])])
        self.assertEqual(len(report_lines), 1)
        self.assertEqual(report_lines.product_id, self.recurring_product)
        self.assertEqual(report_lines.product_uom_qty, 3)
        self.assertEqual(report_lines.price_subtotal, 300)

    def test_report_confirm_upsell_with_other_product(self):
        action = self.original_subscription.prepare_upsell_order()
        upsell_sub = self.env['sale.order'].browse(action['res_id'])
        upsell_sub.order_line = [Command.create({
                'name': self.no_recurring_product.name,
                'product_id': self.no_recurring_product.id,
                'product_uom_qty': 5.0,
                'price_unit': self.no_recurring_product.list_price,
            })]
        upsell_sub.action_confirm()
        self.env.flush_all()

        report_lines = self.env['sale.report'].search([('name', 'in', [self.original_subscription.name, upsell_sub.name])])
        self.assertEqual(len(report_lines), 1)
        recurring_line = report_lines.filtered(lambda l: l.product_id == self.recurring_product)
        self.assertEqual(recurring_line.product_uom_qty, 2)
        self.assertEqual(recurring_line.price_subtotal, 200)

    def test_report_confirm_upsell_with_same_product_and_discount(self):
        action = self.original_subscription.prepare_upsell_order()
        upsell_sub = self.env['sale.order'].browse(action['res_id'])
        upsell_sub.order_line = [Command.create({
                'name': self.recurring_product.name,
                'product_id': self.recurring_product.id,
                'product_uom_qty': 1.0,
                'price_unit': self.recurring_product.list_price,
                'discount': 30,
            })]
        upsell_sub.action_confirm()
        self.env.flush_all()

        report_lines = self.env['sale.report'].search([('name', 'in', [self.original_subscription.name, upsell_sub.name])])
        self.assertEqual(len(report_lines), 1)
        self.assertEqual(report_lines.product_id, self.recurring_product)
        self.assertEqual(report_lines.product_uom_qty, 3)
        self.assertEqual(report_lines.price_subtotal, 300)
        self.assertEqual(upsell_sub.order_line.filtered('discount').price_subtotal, 70)
        # Note: on the Sales report, it is normal to lose the discount given in the upsell.
