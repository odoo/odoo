from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.tests import tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestSubscriptionPlan(TestSubscriptionCommon):

    def test_check_count_of_subscription_items_on_plan(self):
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True}
        SubPlan = self.env['sale.subscription.plan'].with_context(context_no_mail)

        # Create a subscription plan
        sub_monthly_plan = SubPlan.create({
            'name': 'Monthly Plan',
            'billing_period_value': 1,
            'billing_period_unit': 'month'
        })

        # Create subscriptions
        sub_1, sub_2 = self.env['sale.order'].create([{
            'name': 'Test Subscription 1',
            'is_subscription': True,
            'plan_id': sub_monthly_plan.id,
            'partner_id': self.user_portal.partner_id.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'name': "Monthly cheap",
                    'price_unit': 42,
                    'product_uom_qty': 2,
                }),
                Command.create({
                    'product_id': self.product2.id,
                    'name': "Monthly expensive",
                    'price_unit': 420,
                    'product_uom_qty': 3,
                }),
            ]
        }, {
            'name': 'Test Subscription 2',
            'is_subscription': True,
            'plan_id': sub_monthly_plan.id,
            'partner_id': self.user_portal.partner_id.id,
            'order_line': [
                Command.create({
                    'product_id': self.product2.id,
                    'name': "Monthly expensive",
                    'price_unit': 420,
                    'product_uom_qty': 3,
                }),
            ]
        }])

        # Confirm subscriptions
        sub_1.action_confirm()
        sub_2.action_confirm()

        # Verify the count of subscription items
        sub_plan_items = self.env['sale.subscription.plan'].search([('id', '=', sub_monthly_plan.id)])
        self.assertEqual(sub_plan_items.subscription_line_count, 3)
