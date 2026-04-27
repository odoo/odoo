# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from freezegun import freeze_time


from odoo import Command, fields
from odoo.tests import tagged
from odoo.exceptions import UserError

from odoo.addons.sale_commission_subscription.tests.common import TestSaleSubscriptionCommissionCommon


@tagged('post_install', '-at_install')
class TestSaleSubCommissionUser(TestSaleSubscriptionCommissionCommon):

    def test_sub_commission_user_achievement(self):
        with freeze_time('2024-02-02'):
            sub = self.subscription.copy()
            sub.user_id = self.commission_user_1.id
            sub.order_line.price_unit = 500
            sub.start_date = False
            sub.next_invoice_date = False
            self.commission_plan_sub.achievement_ids = self.env['sale.commission.plan.achievement'].create([{
                'type': 'amount_invoiced',
                'rate': 0.1,
                'plan_id': self.commission_plan_sub.id,
                'recurring_plan_id': sub.plan_id.id,
            }])
            sub.action_confirm()
            with self.assertRaises(UserError):
                # achievements based on sold metrics can't be used with recurring plan achievements
                self.commission_plan_sub.achievement_ids = self.env['sale.commission.plan.achievement'].create([{
                'type': 'amount_sold',
                'rate': 0.1,
                'plan_id': self.commission_plan_sub.id,
                'recurring_plan_id': sub.plan_id.id,
            }])
            self.commission_plan_sub.action_approve()
            inv = sub._create_recurring_invoice()
            self.assertAlmostEqual(inv.amount_untaxed, 1000, 2, msg="The untaxed invoiced amount should be equal to 1000")

            achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_sub.id)])
            commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_sub.id)])

            self.assertEqual(len(commissions), 24)
            self.assertEqual(len(achievements), 1, 'The one line should count as an achievement')
            self.assertAlmostEqual(sum(achievements.mapped('achieved')), 100, 2, msg="1000 * 0.1")
            self.assertEqual(achievements.related_res_id, inv.id)
            self.assertEqual(len(commissions), 24)
            self.assertEqual(sum(commissions.mapped('commission')), 100)

        with freeze_time('2024-02-16'):
            action = sub.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])
            upsell_so.order_line.filtered(lambda l: not l.display_type).product_uom_qty = 1
            upsell_so.action_confirm()
            inv2 = upsell_so._create_invoices()
            inv2._post()
            self.assertAlmostEqual(inv2.amount_untaxed, 517.2, 2, msg="The untaxed upsell invoiced amount should be equal to 517.2")
            self.env.invalidate_all()

            achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_sub.id)])
            commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_sub.id)])

            self.assertEqual(len(commissions), 24)
            self.assertEqual(len(achievements), 2, 'Two line should count as an achievement')
            self.assertAlmostEqual(sum(achievements.mapped('achieved')), 151.72, 2, msg="previous invoice + upsell pro-rata")
            self.assertEqual(sorted(achievements.mapped('related_res_id')), sorted([inv.id, inv2.id]))
            self.assertEqual(len(commissions), 24)
            self.assertAlmostEqual(sum(commissions.mapped('commission')), 151.72, 2)

        with freeze_time('2024-03-02'):
            inv3 = sub._create_recurring_invoice()
            self.env.invalidate_all()
            achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_sub.id)])
            achievements = achievements.filtered(lambda x: x.related_res_id == inv3.id and x.related_res_model == 'account.move')
            commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_sub.id)])
            self.assertEqual(len(achievements), 1, 'The one line should count as an achievement')
            commission_period = commissions.filtered(lambda x: x.target_id == achievements.target_id)

            self.assertEqual(len(commission_period), 2, "2 commissions for two users")
            self.assertEqual(sum(achievements.mapped('achieved')), 200, 'Regular invoice (doubled quantity)')
            self.assertEqual(achievements.related_res_id, inv3.id)
            self.assertEqual(sum(commission_period.mapped('commission')), 200, "One user has achieved and not the other one")

    @freeze_time('2024-02-02')
    def test_multiple_plans_conditions(self):
        sub = self.subscription.copy()
        sub.user_id = self.commission_user_1.id
        sub.order_line.price_unit = 500
        sub.start_date = False
        sub.next_invoice_date = False
        sub.action_confirm()
        self.commission_plan_sub.achievement_ids = self.env['sale.commission.plan.achievement'].create([{
            'type': 'amount_invoiced',
            'rate': 0.1,
            'plan_id': self.commission_plan_sub.id,
            'recurring_plan_id': sub.plan_id.id,
        }])
        self.commission_plan_user.achievement_ids = self.env['sale.commission.plan.achievement'].create([{
            'type': 'amount_invoiced',
            'rate': 0.1,
            'plan_id': self.commission_plan_user.id,
        }])

        self.commission_plan_user.action_approve()
        self.commission_plan_sub.action_approve()
        inv_sub = sub._create_recurring_invoice()
        self.assertAlmostEqual(inv_sub.amount_untaxed, 1000, 2, msg="The amount of the recurring invoice is 1000")
        other_sale = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.commission_user_1.id,
            'order_line': [Command.create({
                'product_id': self.commission_product_1.id,
                'product_uom_qty': 1,
                'price_unit': 100,
            })],
        })
        other_sale.action_confirm()
        inv2 = other_sale._create_invoices()
        self.assertAlmostEqual(inv2.amount_untaxed, 100, 2, msg="The amount of the non recurring invoice is 100")
        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_sub.id)])
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_sub.id)])

        self.assertEqual(len(commissions), 24, "24 commissions for two users")
        self.assertEqual(sum(achievements.mapped('achieved')), 100, 'Regular invoice, 10 percent of 1000')
        self.assertEqual(achievements.related_res_id, inv_sub.id)
        self.assertEqual(sum(commissions.mapped('commission')), 100, "One user has achieved and not the other one")


        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id)])
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])
        # this plan will take both invoices: subscription and the other one because no recurring plan is defined
        self.assertEqual(len(commissions), 24, "24 commissions for two users")
        self.assertAlmostEqual(inv2.amount_untaxed, 100, 2, msg="The amount of the non recurring invoice is 100")
        self.assertEqual(sum(achievements.mapped('achieved')), 110, 'Subscription invoice provide 100 and non recurring one provives 10')
        self.assertEqual(sorted(achievements.mapped('related_res_id')), sorted([inv2.id, inv_sub.id]))
        self.assertEqual(sum(commissions.mapped('commission')), 110, "One user has achieved and not the other one")


    @freeze_time('2024-02-02')
    def test_multiple_achievements(self):
        # this test makes sure all achievements are summed even if one product is in several achievements for example
        category = self.env['product.category'].create({
            'name': 'Test Category',
        })
        self.commission_plan_sub.search([]).action_draft()
        sub = self.subscription.copy()
        sub.user_id = self.commission_user_1.id
        sub.order_line[1].unlink()
        product = sub.order_line.product_id
        product.categ_id = category.id
        sub.order_line.price_unit = 500
        sub.start_date = False
        sub.next_invoice_date = False
        self.commission_plan_sub.achievement_ids = self.env['sale.commission.plan.achievement'].create([
            {
                'type': 'amount_invoiced',
                'rate': 0.1,
                'plan_id': self.commission_plan_sub.id,
                'recurring_plan_id': sub.plan_id.id,
            }, {
                'type': 'amount_invoiced',
                'rate': 0.2,
                'plan_id': self.commission_plan_sub.id,
                'product_id': product.id,
            }, {
                'type': 'amount_invoiced',
                'rate': 0.3,
                'plan_id': self.commission_plan_sub.id,
                'product_categ_id': category.id,
            }

        ])
        self.commission_plan_user.achievement_ids = self.env['sale.commission.plan.achievement'].create([
            {
                'type': 'amount_invoiced',
                'rate': 0.1,
                'plan_id': self.commission_plan_user.id,
                'product_id': product.id,
            }, {
                'type': 'amount_invoiced',
                'rate': 0.2,
                'plan_id': self.commission_plan_user.id,
                'product_categ_id': category.id,
            }
        ])
        self.commission_plan_user.action_approve()
        self.commission_plan_sub.action_approve()
        sub.action_confirm()
        inv = sub._create_recurring_invoice()
        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_sub.id)])
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_sub.id)])
        self.assertAlmostEqual(inv.amount_untaxed, 500, 2, msg="The invoice amount should be equal to 500")
        # this plan will take both invoices: subscription and the other one because no recurring plan is defined
        self.assertEqual(len(commissions), 24, "24 commissions for two users")
        self.assertEqual(sum(achievements.mapped('achieved')), 300, 'Subscription invoice provide 300: 500*0.1 + 500*0.2+500*0.3')
        self.assertEqual(achievements.related_res_id, inv.id)
        self.assertEqual(sum(commissions.mapped('commission')), 300, "One user has achieved and not the other one")

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id)])
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])
        self.assertAlmostEqual(inv.amount_untaxed, 500, 2, msg="The invoice amount should be equal to 500")
        # this plan will take both invoices: subscription and the other one because no recurring plan is defined
        self.assertEqual(len(commissions), 24, "24 commissions for two users")
        self.assertEqual(sum(achievements.mapped('achieved')), 150, 'invoice provide 150: 500*0.1 + 500*0.2')
        self.assertEqual(achievements.related_res_id, inv.id)
        self.assertEqual(sum(commissions.mapped('commission')), 150, "One user has achieved and not the other one")
