# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.tests import tagged
from odoo import Command, fields
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon


@tagged('-at_install', 'post_install')
class TestSubscriptionStockCommon(TestSubscriptionCommon, ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        SaleOrder = cls.env['sale.order']
        Product = cls.env['product.product']

        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        cls.plan_3_months = cls.env['sale.subscription.plan'].create({'billing_period_value': 3, 'billing_period_unit': 'month'})

        # Test user dedicated to avoid sharing moves and batches
        TestUsersEnv = cls.env['res.users'].with_context({'no_reset_password': True})
        group_portal_id = cls.env.ref('base.group_portal').id
        cls.country_belgium = cls.env.ref('base.be')
        cls.user_portal2 = TestUsersEnv.create({
            'name': 'Beatrice Portal 2',
            'login': 'Beatrice2',
            'country_id': cls.country_belgium.id,
            'email': 'beatrice.employee2@example.com',
            'groups_id': [(6, 0, [group_portal_id])],
            'property_account_payable_id': cls.account_payable.id,
            'property_account_receivable_id': cls.account_receivable.id,
            'company_id': cls.company_data['company'].id,
        })

        # Pricing

        pricing_commands = [
            Command.create({
                'plan_id': cls.plan_month.id,
                'price': 45,
            }),
            Command.create({
                'plan_id': cls.plan_3_months.id,
                'price': 50,
            })
        ]

        cls.pricing_1month = cls.env['sale.subscription.pricing'].create({
            'plan_id': cls.plan_month.id,
            'price': 45,
        })

        cls.pricing_3month = cls.env['sale.subscription.pricing'].create({
            'plan_id': cls.plan_3_months.id,
            'price': 50,
        })

        # Product

        cls.sub_product_order = Product.create({
            'name': "Subscription consumable invoiced on order",
            'standard_price': 0.0,
            'type': 'consu',
            'uom_id': cls.uom_unit.id,
            'invoice_policy': 'order',
            'recurring_invoice': True,
            'product_subscription_pricing_ids': pricing_commands,
        })

        cls.sub_product_order_2 = Product.create({
            'name': "Subscription consumable invoiced on order #2",
            'standard_price': 0.0,
            'type': 'consu',
            'uom_id': cls.uom_unit.id,
            'invoice_policy': 'order',
            'recurring_invoice': True,
            'product_subscription_pricing_ids': pricing_commands,
        })

        cls.sub_product_delivery = Product.create({
            'name': "Subscription consumable invoiced on delivery",
            'standard_price': 0.0,
            'type': 'consu',
            'uom_id': cls.uom_unit.id,
            'invoice_policy': 'delivery',
            'recurring_invoice': True,
            'product_subscription_pricing_ids': pricing_commands,
        })

        cls.product_non_recurring = Product.create({
            'name': "Consumable invoiced on order",
            'standard_price': 30.0,
            'type': 'consu',
            'uom_id': cls.uom_unit.id,
            'invoice_policy': 'order',
        })

        # SO

        cls.subscription_order = SaleOrder.create({
            'name': 'Order',
            'is_subscription': True,
            'partner_id': cls.user_portal.partner_id.id,
            'plan_id': cls.plan_month.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
            'order_line': [Command.create({
                'product_id': cls.sub_product_order.id,
                'product_uom_qty': 1,
                'tax_id': [Command.clear()],
            })]
        })

        cls.subscription_delivery = SaleOrder.create({
            'name': 'Delivery',
            'is_subscription': True,
            'partner_id': cls.user_portal.partner_id.id,
            'plan_id': cls.plan_month.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
            'order_line': [Command.create({
                'product_id': cls.sub_product_delivery.id,
                'product_uom_qty': 1,
                'tax_id': [Command.clear()],
            })]
        })
        cls.context = {
            'active_model': 'sale.order',
            'active_ids': [cls.subscription_order.id],
            'active_id': cls.subscription_order.id,
            'default_journal_id': cls.company_data['default_journal_sale'].id,
        }

        # update status
        # cls.subscription_delivery._compute_is_deferred()

        with freeze_time("2022-03-02"):
            cls.subscription_order.write({'start_date': fields.date.today(), 'next_invoice_date': False})
            cls.subscription_delivery.write({'start_date': fields.date.today(), 'next_invoice_date': False})
            cls.subscription_order.action_confirm()
            cls.subscription_delivery.action_confirm()
            cls.subscription_order.picking_ids.move_ids.write({'quantity': cls.subscription_order.order_line.product_uom_qty, 'picked': True})
            cls.subscription_delivery.picking_ids.move_ids.write({'quantity': cls.subscription_delivery.order_line.product_uom_qty, 'picked': True})
            cls.subscription_order.picking_ids._action_done()
            cls.subscription_delivery.picking_ids._action_done()

    def simulate_period(self, subscription, date, move_qty=False):
        with freeze_time(date):
            today = fields.Date.today()
            invoice = subscription._create_recurring_invoice()
            if invoice and invoice.state == 'draft':
                invoice.action_post()
            picking = subscription.picking_ids and subscription.picking_ids.filtered(lambda picking: picking.date.date() == today)
            self.validate_picking_moves(picking, move_qty=move_qty)

        return invoice, picking

    def validate_picking_moves(self, picking, move_qty=False):
        if picking:
            for move in picking.move_ids:
                move.write({'quantity': move_qty or move.product_uom_qty, 'picked': True})
            picking._action_done()
            picking.move_ids.state = 'done'
