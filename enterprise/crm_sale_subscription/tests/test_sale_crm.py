from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.fields import Command


class TestCrmSubscription(TestCrmCommon):

    def test_crm_sale_subscription_revenue(self):
        """ Test the updation of the expected_revenue and the recurring_revenue when quotation is confirmed.
        If the expected_revenue of the lead is smaller than the nonrecurring total of quote, which we are confirming upadte it with that.
        If the recurring_revenue of the lead is smaller than the recurring monthly of quote, which we are confirming upadte it with,
        Case 1: when no recurring plan is set on lead update it with recurring monthly.
        Case 2 when recurring plan is set on the lead update it with (recurring monthly * number of months).
        e.g. If the lead has an expected_revenue of $40, recurring_revenues of 10$ and doesn't contain any recurring plan,
        Quote 1: nonrecurring total $45, recurring monthly $12.
        Then the expected_revenue would be updated from $40 to $45 and recurring_revenue from $10 to $12.
        """
        product1, product2, recurring_product1, recurring_product2 = self.env['product.template'].create([{
            'name': 'Test product1',
            'list_price': 100.0,
        }, {
            'name': 'Test product2',
            'list_price': 200.0,
        }, {
            'name': 'Recurring product1',
            'type': 'service',
            'recurring_invoice': True,
            'list_price': 10.0,
        }, {
            'name': 'Recurring product2',
            'type': 'service',
            'recurring_invoice': True,
            'list_price': 20.0,
        }])

        subscription_plan = self.env['sale.subscription.plan'].create({
            'name': 'Monthly',
            'billing_period_value': 1,
            'billing_period_unit': 'month',
        })

        crm_recurring_plan = self.env['crm.recurring.plan'].create({
            'name': 'Test yearly plan',
            'number_of_months': 12,
        })

        my_pricelist = self.env['product.pricelist'].create({
            'name': 'Rupee',
            'currency_id': self.ref('base.INR')
        })
        pricelist_expected_by_lead = self.env['product.pricelist'].create({
            'name': 'Rupee',
            'currency_id': self.ref('base.USD')
        })

        so_values = {
            'partner_id': self.env.user.partner_id.id,
            'opportunity_id': self.lead_1.id,
            'plan_id': subscription_plan.id,
        }
        so1, so2 = self.env['sale.order'].create([{
            **so_values,
            'pricelist_id': my_pricelist.id,
            'order_line': [
                Command.create({
                    'product_id': product.product_variant_id.id,
                }) for product in [product1, recurring_product1]
            ],
        }, {
            **so_values,
            'pricelist_id': pricelist_expected_by_lead.id,
            'order_line': [
                Command.create({
                    'product_id': product.product_variant_id.id,
                }) for product in [product2, recurring_product2]
            ],
        }])

        self.env.user.groups_id = [Command.set(self.env.ref("crm.group_use_recurring_revenues").ids)]
        self.assertEqual(self.lead_1.expected_revenue, 0)
        self.assertFalse(self.lead_1.recurring_plan)

        # Revenue should not be updated when the currency of sale order is different from lead.
        so1.action_confirm()
        self.assertEqual(self.lead_1.expected_revenue, 0)
        self.assertEqual(self.lead_1.recurring_revenue, 0)
        # Revenue should be updated when the currency is same also checking without crm_recurring_plan.
        so2.action_confirm()
        self.assertEqual(self.lead_1.recurring_plan.id, self.ref("crm.crm_recurring_plan_monthly"))
        self.assertEqual(self.lead_1.recurring_revenue, 20)
        self.assertEqual(self.lead_1.expected_revenue, 200)

        # Checking with crm_recurring_plan.
        self.lead_1.write({'recurring_plan': crm_recurring_plan, 'recurring_revenue': 0, 'expected_revenue': 0})
        so2.write({'state': 'draft'})
        so2.action_confirm()
        self.assertEqual(self.lead_1.expected_revenue, 200)
        self.assertEqual(self.lead_1.recurring_revenue, 240)
