# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.website.tools import MockRequest
from odoo.tests import Form, freeze_time
from odoo.exceptions import UserError
from .common import TestWebsiteSaleSubscriptionCommon

@tagged('post_install', '-at_install')
class TestWebsiteSaleSubscription(TestWebsiteSaleSubscriptionCommon):

    def test_cart_update_so_reccurence(self):
        self.env['product.pricelist'].sudo().search([('active', '=', True)]).action_archive()
        # Product not recurring
        product = self.env['product.template'].with_context(website_id=self.current_website.id).create({
            'name': 'Non-recurring Product',
            'list_price': 15,
            'type': 'service',
        })
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
        })

        # Mocking to check if error raised on Website when adding
        # 2 subscription product with different recurrence
        with MockRequest(self.env, website=self.current_website, sale_order_id=so.id):
            so = self.current_website.sale_get_order()
            self.assertFalse(so.plan_id)
            so._cart_update(product_id=product.product_variant_ids.id, add_qty=1)
            self.assertFalse(so.plan_id)
            so._cart_update(product_id=self.sub_product.product_variant_ids.id, add_qty=1)
            self.assertEqual(so.plan_id, self.plan_week)
            with self.assertRaises(UserError, msg="You can't add a subscription product to a sale order with another recurrence."):
                so._cart_update(product_id=self.sub_product_2.product_variant_ids.id, add_qty=1)
            so._cart_update(product_id=self.sub_product.product_variant_ids.id, add_qty=None, set_qty=0)
            self.assertFalse(so.plan_id)
            so._cart_update(product_id=self.sub_product_2.product_variant_ids.id, add_qty=1)
            self.assertEqual(so.plan_id, self.plan_month)
            so._cart_update(product_id=self.sub_product_2.product_variant_ids.id, add_qty=None, set_qty=0)
            self.assertFalse(so.plan_id)

    def test_combination_info_product(self):
        self.sub_product = self.sub_product.with_context(website_id=self.current_website.id)

        with MockRequest(self.env, website=self.current_website):
            combination_info = self.sub_product._get_combination_info()
            self.assertEqual(combination_info['price'], 5)
            self.assertTrue(combination_info['is_subscription'])
            self.assertEqual(combination_info['subscription_default_pricing_plan_id'], self.plan_week.id)
            self.assertEqual(combination_info['subscription_default_pricing_price'], 'Weekly: $ 5.00')

    def test_combination_info_variant_products(self):
        template = self.sub_with_variants.with_context(website_id=self.current_website.id)
        combination_info = template.product_variant_ids[0]._get_combination_info_variant()
        self.assertEqual(combination_info['price'], 10)
        self.assertTrue(combination_info['is_subscription'])
        self.assertEqual(combination_info['subscription_default_pricing_plan_id'], self.plan_week.id)
        self.assertEqual(combination_info['subscription_default_pricing_price'], 'Weekly: $ 10.00')

        combination_info_variant_2 = template.product_variant_ids[-1]._get_combination_info_variant()
        self.assertEqual(combination_info_variant_2['price'], 25)
        self.assertTrue(combination_info_variant_2['is_subscription'])
        self.assertEqual(combination_info_variant_2['subscription_default_pricing_plan_id'], self.plan_month.id)
        self.assertEqual(combination_info_variant_2['subscription_default_pricing_price'], 'Monthly: $ 25.00')

    def test_combination_info_multi_pricelist(self):
        product = self.sub_product_3.with_context(website_id=self.current_website.id)

        with MockRequest(self.env, website=self.current_website, website_sale_current_pl=self.pricelist_111.id):
            combination_info = product._get_combination_info(only_template=True)
            self.assertEqual(combination_info['price'], 111)

        self.current_website.invalidate_recordset(['pricelist_id'])
        with MockRequest(self.env, website=self.current_website, website_sale_current_pl=self.pricelist_222.id):
            combination_info = product._get_combination_info(only_template=True)
            self.assertEqual(combination_info['price'], 222)

    def test_delivery_line_not_applied_prorata_discount(self):
        """Ensure delivery lines keep their original price and are not prorated in subscription invoices and upsell order."""
        with freeze_time("2025-09-15"):
            sub = self.subscription
            sub.plan_id.billing_first_day = True

            # Create a custom delivery product and carrier
            delivery_categ = self.env.ref('delivery.product_category_deliveries')
            delivery_product = self.env['product.product'].create({
                'name': "Carrier Product",
                'type': 'service',
                'recurring_invoice': True,
                'categ_id': delivery_categ.id,
                'sale_ok': False,
                'purchase_ok': False,
                'invoice_policy': 'order',
                'list_price': 5.0,
            })
            delivery = self.env['delivery.carrier'].create({
                'name': "Test Carrier",
                'fixed_price': 5.0,
                'delivery_type': 'fixed',
                'product_id': delivery_product.id,
            })

            # Add delivery to subscription order
            delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
                'default_order_id': sub.id,
                'default_carrier_id': delivery.id,
            }))
            choose_delivery = delivery_wizard.save()
            choose_delivery.button_confirm()

            # Ensure carrier line is added on order
            delivery_line = sub.order_line.filtered(lambda ln: ln.product_id == delivery_product)
            self.assertTrue(delivery_line, "Carrier line should be added to the subscription order")

            # Confirm subscription order
            sub.action_confirm()
            self.assertEqual("2025-09-15", sub.next_invoice_date.strftime("%Y-%m-%d"), "On confirmation, next_invoice_date")
            self.assertEqual(delivery_line.price_total, 5.75, "Delivery product price should stay fixed before invoicing")

            # Generate prorated invoice
            inv = sub._create_recurring_invoice()
            inv_delivery_line = inv.invoice_line_ids.filtered(lambda ln: ln.product_id == delivery_product)
            self.assertEqual("2025-10-01", sub.next_invoice_date.strftime("%Y-%m-%d"),
                "After prorated period, next_invoice_date should move to the 1st day of the next month")
            # Verify delivery product not prorated
            self.assertEqual(inv_delivery_line.price_total, 5.75, "Delivery line should remain unchanged(not prorated) in the invoice")

            sub1 = sub.copy()
            sub1.plan_id.billing_first_day = False
            sub1.action_confirm()
            sub1._create_recurring_invoice()
        with freeze_time("2025-09-20"):
            action = sub1.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])
            upsell_delivery_line = upsell_so.order_line.filtered(lambda ln: ln.product_id == delivery_product)
            upsell_delivery_line.product_uom_qty = 1.0
            self.assertEqual(upsell_delivery_line.price_total, 5.75, "Delivery product price should stay fixed")

    def test_combination_info_skips_archived_plan(self):
        # Archive the month plan (so only year should be used)
        self.plan_month.action_archive()
        product = self.sub_product_tmpl.with_context(website_id=self.current_website.id)

        with MockRequest(self.env, website=self.current_website):
            combination_info = product._get_combination_info()
            self.assertTrue(combination_info['is_subscription'])
            self.assertEqual(combination_info['subscription_default_pricing_plan_id'], self.plan_year.id)
