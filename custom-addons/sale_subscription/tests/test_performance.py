# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.tests.common import users, warmup, tagged


@tagged('sub_perf', 'post_install', '-at_install')
class TestSubscriptionPerformance(TestSubscriptionCommon):

    @users('__system__')
    @warmup
    def test_recurring_order_creation_perf(self):
        # Prevent trigger base_automation actions
        self.env['sale.order.alert'].search([]).unlink()
        ORDER_COUNT = 100
        partners = self.env['res.partner'].create([{
            'name': 'Jean-Luc %s' % (idx),
            'email': 'jean-luc-%s@opoo.com' % (idx)
        } for idx in range(ORDER_COUNT)])
        with self.assertQueryCount(__system__=2230):
            sale_orders = self.env['sale.order'].create([{
                'name': "SO %s" % idx,
                'partner_id': partners[idx].id,
                'plan_id': self.plan_month.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'order_line': [
                    (0, 0, {
                        'name': self.company_data['product_order_cost'].name,
                        'product_id': self.product.id,
                        'product_uom_qty': 2,
                        'qty_delivered': 1,
                        'product_uom': self.company_data['product_order_cost'].uom_id.id,
                        'price_unit': self.company_data['product_order_cost'].list_price,
                    }),
                    (0, 0, {
                        'name': self.company_data['product_delivery_cost'].name,
                        'product_id': self.product.id,
                        'product_uom_qty': 4,
                        'qty_delivered': 1,
                        'product_uom': self.company_data['product_delivery_cost'].uom_id.id,
                        'price_unit': self.company_data['product_delivery_cost'].list_price,
                    }),
                ],

            } for idx in range(ORDER_COUNT)])

            sale_orders.action_confirm()

        # 7731 with only sale_subscription
        # But as the invoices are created one by one,
        # adding a request on _create_invoice has a big impact on the
        # global count
        # with self.assertQueryCount(__system__=9133):
        #     sale_orders._create_recurring_invoice()

        # non recurring products
        product_tmpl = self.env['product.template'].create({
            'name': 'Non recurring Product',
            'type': 'service',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        product_id = product_tmpl.product_variant_id
        NR_COUNT = 25
        non_recuring_sale_orders = self.env['sale.order'].create([{
            'name': "SO %s" % idx,
            'partner_id': partners[idx].id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [
                (0, 0, {
                    'name': self.company_data['product_order_cost'].name,
                    'product_id': product_id.id,
                    'product_uom_qty': 2,
                    'qty_delivered': 1,
                    'product_uom': self.company_data['product_order_cost'].uom_id.id,
                    'price_unit': self.company_data['product_order_cost'].list_price,
                }),
            ],

        } for idx in range(NR_COUNT)])
