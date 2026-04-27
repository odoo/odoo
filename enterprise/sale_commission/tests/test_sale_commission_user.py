# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from freezegun import freeze_time

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale_commission.tests.test_sale_commission_common import TestSaleCommissionCommon


@tagged('post_install', '-at_install')
class TestSaleCommissionUser(TestSaleCommissionCommon):

    @freeze_time('2024-02-02')
    def test_commission_user_achievement(self):
        self.commission_plan_user.write({
            'periodicity': 'month',
            'type': 'achieve',
            'user_type': 'person',
        })

        self.commission_plan_user.action_approve()

        self.commission_plan_user.achievement_ids = self.env['sale.commission.plan.achievement'].create([{
            'type': 'amount_sold',
            'rate': 0.04,
            'plan_id': self.commission_plan_user.id,
        }, {
            'type': 'amount_invoiced',
            'rate': 0.06,
            'plan_id': self.commission_plan_user.id,
        }, {
            'type': 'amount_sold',
            'rate': 0.1,
            'product_id': self.commission_product_2.id,
            'plan_id': self.commission_plan_user.id,
        }])

        SO = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.commission_user_1.id,
            'order_line': [Command.create({
                'product_id': self.commission_product_1.id,
                'product_uom_qty': 10,
                'price_unit': 200,
            })],
        })

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id)])
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])

        self.assertFalse(achievements, 'SO has not been confirmed yet, there should be no achievement.')
        self.assertEqual(len(commissions), 24, 'SO has not been confirmed yet, we should have only forecasts.')

        SO.action_confirm()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id)])
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])

        self.assertEqual(len(achievements), 1, 'The one line should count as an achievement')
        self.assertEqual(sum(achievements.mapped('achieved')), 80, '0.04 * 2000 = 80')
        self.assertEqual(achievements.related_res_id, SO.id)
        self.assertEqual(len(commissions), 24)
        self.assertEqual(sum(commissions.mapped('commission')), 80)

        SO.date_order = "2024-02-01 10:00:00"  # First day of the monthly period
        self.env.invalidate_all()
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id), ('date_to', '=', '2024-02-29')])
        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id), ('date', '>=', '2024-02-01'), ('date', '<=', '2024-02-29')])
        self.assertEqual(sum(commissions.mapped('achieved')), 80)
        self.assertEqual(len(achievements), 1)

        SO.date_order = "2024-02-29 10:00:00"  # Last day of the monthly period
        self.env.invalidate_all()
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id), ('date_to', '=', '2024-02-29')])
        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id), ('date', '>=', '2024-02-01'), ('date', '<=', '2024-02-29')])
        self.assertEqual(sum(commissions.mapped('achieved')), 80)
        self.assertEqual(len(achievements), 1)

        AM = SO._create_invoices()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id)]).\
            filtered(lambda x: x.related_res_id == AM.id and x.related_res_model == 'account.move')
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])

        self.assertEqual(len(achievements), 1, 'There should be one new achievement')
        self.assertEqual(sum(achievements.mapped('achieved')), 120, '0.06 * 2000 = 120')
        self.assertEqual(len(commissions), 24)
        self.assertEqual(sum(commissions.mapped('commission')), 200)

        SO2 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.commission_user_1.id,
            'order_line': [Command.create({
                'product_id': self.commission_product_2.id,
                'product_uom_qty': 10,
                'price_unit': 200,
            })],
        })
        SO2.action_confirm()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id)]).\
            filtered(lambda x: x.related_res_id == SO2.id and x.related_res_model == 'sale.order')
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])

        self.assertEqual(len(achievements), 1)
        self.assertEqual(sum(achievements.mapped('achieved')), 280, '0.04 * 2000 + 0.1 * 2000 = 280')
        self.assertEqual(len(commissions), 24)
        self.assertEqual(sum(commissions.mapped('commission')), 480, '200 + 280')

        AM2 = SO2._create_invoices()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id)]).\
            filtered(lambda x: x.related_res_id == AM2.id and x.related_res_model == 'account.move')
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])

        self.assertEqual(len(achievements), 1, 'There should be one new achievement')
        self.assertEqual(sum(achievements.mapped('achieved')), 120, '0.06 * 2000 = 120')
        self.assertEqual(len(commissions), 24)
        self.assertEqual(sum(commissions.mapped('commission')), 600)

        # Check that a refund invoice creates a negative achievement
        AM.action_post()
        refund_wizard = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=AM.ids).create({
            'journal_id': AM.journal_id.id,
        })
        refund_result = refund_wizard.reverse_moves()
        refund_move_id = refund_result['res_id']
        self.env.invalidate_all()

        refund_achievement = self.env['sale.commission.achievement.report'].search([
            ('plan_id', '=', self.commission_plan_user.id),
            ('related_res_id', '=', refund_move_id),
            ('related_res_model', '=', 'account.move')
        ])

        self.assertEqual(len(refund_achievement), 1)
        self.assertEqual(refund_achievement['achieved'], -120, '-0.06 * 2000 = -120')
        self.assertEqual(sum(commissions.mapped('commission')), 480, '600 - 120 = 480')

    @freeze_time('2024-02-02')
    def test_commission_user_target(self):
        self.commission_plan_user.write({
            'periodicity': 'month',
            'type': 'target',
            'user_type': 'person',
            'commission_amount': 2500,
        })

        self.commission_plan_user.achievement_ids = self.env['sale.commission.plan.achievement'].create([{
            'type': 'amount_sold',
            'rate': 0.4,
            'plan_id': self.commission_plan_user.id,
        }, {
            'type': 'amount_invoiced',
            'rate': 0.6,
            'plan_id': self.commission_plan_user.id,
        }, {
            'type': 'amount_sold',
            'rate': 1,
            'product_id': self.commission_product_2.id,
            'plan_id': self.commission_plan_user.id,
        }])

        self.commission_plan_user.target_ids.amount = 2000

        # There is already a level 0 at 0$, level 0.5 at 0$ and level 1 at 2500$ by default
        self.commission_plan_user.target_commission_ids += self.env['sale.commission.plan.target.commission'].create([{
            'target_rate': 2,
            'amount': 3500,
            'plan_id': self.commission_plan_user.id,
        }, {
            'target_rate': 3,
            'amount': 4000,
            'plan_id': self.commission_plan_user.id,
        }])
        self.commission_plan_user.action_approve()

        SO = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.commission_user_1.id,
            'order_line': [Command.create({
                'product_id': self.commission_product_1.id,
                'product_uom_qty': 10,
                'price_unit': 200,
            })],
        })

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id)])
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])

        self.assertFalse(achievements, 'SO has not been confirmed yet, there should be no achievement.')
        self.assertEqual(len(commissions), 24, 'SO has not been confirmed yet, there should be no commission.')

        SO.action_confirm()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id)])
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])

        self.assertEqual(len(achievements), 1, 'The one line should count as an achievement')
        self.assertEqual(sum(commissions.mapped('achieved')), 800, '0.4 * 2000 = 800')
        self.assertEqual(len(commissions), 24)
        self.assertEqual(sum(commissions.mapped('achieved')), 800)
        self.assertEqual(sum(commissions.mapped('commission')), 0, 'Achieved Rate(0.4) < 0.5')

        AM = SO._create_invoices()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id)]).\
            filtered(lambda x: x.related_res_id == AM.id and x.related_res_model == 'account.move')
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])

        self.assertEqual(len(achievements), 1, 'There should be one new achievement')
        self.assertEqual(sum(achievements.mapped('achieved')), 1200, '0.06 * 2000 = 120')
        self.assertEqual(len(commissions), 24)
        self.assertEqual(sum(commissions.mapped('achieved')), 2000)
        self.assertEqual(sum(commissions.mapped('commission')), 2500, 'We reached the 1st level')

        SO2 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.commission_user_1.id,
            'order_line': [Command.create({
                'product_id': self.commission_product_2.id,
                'product_uom_qty': 10,
                'price_unit': 200,
            })],
        })
        SO2.action_confirm()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id)]).\
            filtered(lambda x: x.related_res_id == SO2.id and x.related_res_model == 'sale.order')
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])

        self.assertEqual(len(achievements), 1)
        self.assertEqual(sum(achievements.mapped('achieved')), 2800, '0.4 * 2000 + 1 * 2000 = 2800')
        self.assertEqual(len(commissions), 24)
        self.assertEqual(sum(commissions.mapped('achieved')), 4800)
        self.assertEqual(sum(commissions.mapped('commission')), 3700, 'We have reached the 2nd level,'
                                                       'Achieved Rate = 2.4'
                                                       'Amount = 3500 (AR = 2) + 200 (AR-2 * 500)')

        AM2 = SO2._create_invoices()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id)]).\
            filtered(lambda x: x.related_res_id == AM2.id and x.related_res_model == 'account.move')
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])

        self.assertEqual(len(achievements), 1, 'There should be one new achievement')
        self.assertEqual(sum(achievements.mapped('achieved')), 1200, '0.6 * 2000 = 1200')
        self.assertEqual(len(commissions), 24)
        self.assertEqual(sum(commissions.mapped('achieved')), 6000)
        self.assertEqual(sum(commissions.mapped('commission')), 4000, 'We have reached the 3rd level')

    @freeze_time('2024-02-02')
    def test_commission_user_achievement_SO_different_currency(self):
        self.commission_plan_user.write({
            'periodicity': 'month',
            'type': 'achieve',
            'user_type': 'person',
        })

        self.commission_plan_user.action_approve()

        new_currency = self.env['res.currency'].create({'name': 'new currency', 'symbol': 'NC'})
        self.env['res.currency.rate'].create({
            'currency_id': new_currency.id,
            'rate': 2,  # 2 NC = 1 $
        })
        new_currency_pricelist = self.env['product.pricelist'].create({'name': 'NC', 'currency_id': new_currency.id})

        self.commission_plan_user.achievement_ids = self.env['sale.commission.plan.achievement'].create([{
            'type': 'amount_sold',
            'rate': 1,
            'plan_id': self.commission_plan_user.id,
        }])

        SO = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.commission_user_1.id,
            'order_line': [Command.create({
                'product_id': self.commission_product_1.id,
                'product_uom_qty': 10,
                'price_unit': 200,
            })],
            'pricelist_id': new_currency_pricelist.id,
        })

        SO.action_confirm()
        self.env.invalidate_all()

        self.assertEqual(SO.currency_id, new_currency)

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_user.id)])
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])

        self.assertEqual(len(achievements), 1, 'The one line should count as an achievement')
        self.assertEqual(sum(achievements.mapped('achieved')), 1000, '200 * 10 * 0.5')
        self.assertEqual(achievements.currency_id, self.commission_plan_user.currency_id, 'achievement should be in the SO currency')
        self.assertEqual(achievements.related_res_id, SO.id)
        self.assertEqual(len(commissions), 24)
        self.assertEqual(sum(commissions.mapped('commission')), 1000, "2000 * 0.5, currency conversion")

    @freeze_time('2024-02-02')
    def test_edit_forecast(self):
        self.commission_plan_user.write({
            'periodicity': 'month',
            'type': 'achieve',
            'user_type': 'person',
        })
        self.commission_plan_user.action_approve()

        self.commission_plan_user.achievement_ids = self.env['sale.commission.plan.achievement'].create([{
            'type': 'amount_sold',
            'rate': 0.04,
            'plan_id': self.commission_plan_user.id,
        }, {
            'type': 'amount_invoiced',
            'rate': 0.06,
            'plan_id': self.commission_plan_user.id,
        }])

        SO = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.commission_user_1.id,
            'order_line': [Command.create({
                'product_id': self.commission_product_1.id,
                'product_uom_qty': 10,
                'price_unit': 200,
            })],
        })

        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])

        self.assertEqual(len(commissions), 24, 'SO has not been confirmed yet, there should be no commission.')

        SO.action_confirm()
        self.env.invalidate_all()

        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])

        self.assertEqual(sum(commissions.mapped('forecast')), 0)
        commissions.write({'forecast': 100})
        self.assertEqual(sum(commissions.mapped('forecast')), 2400, "Each forecast line has a value equal to 100")

        self.env.invalidate_all()
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])

        self.assertEqual(sum(commissions.mapped('forecast')), 2400)
        commissions.write({'forecast': 200})
        self.assertEqual(sum(commissions.mapped('forecast')), 4800)

        self.env.invalidate_all()
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_user.id)])
        self.assertEqual(sum(commissions.mapped('forecast')), 4800)


    @freeze_time('2024-02-02')
    def test_plan_other(self):
        self.env['sale.commission.plan'].search([]).unlink()
        commission_full_year = self.env['sale.commission.plan'].create({
            'name': "Full year",
            'company_id': self.env.company.id,
            'date_from': datetime.date(year=2024, month=1, day=1),
            'date_to': datetime.date(year=2024, month=12, day=31),
            'periodicity': 'month',
            'type': 'target',
            'user_type': 'person',
            'commission_amount': 2500,
            'user_ids': [Command.create({
                'user_id': self.commission_user_1.id,
            })],
        })
        commission_full_year.action_approve()
        commission_six_month = self.env['sale.commission.plan'].create({
            'name': "Six month",
            'company_id': self.env.company.id,
            'date_from': datetime.date(year=2024, month=3, day=1),
            'date_to': datetime.date(year=2024, month=9, day=30),
            'periodicity': 'month',
            'type': 'target',
            'user_type': 'person',
            'commission_amount': 2500,
            'user_ids': [Command.create({
                'user_id': self.commission_user_1.id,
            })],
        })
        self.assertEqual(commission_six_month.user_ids.other_plans, commission_full_year)
        commission_2023_overflow = self.env['sale.commission.plan'].create({
            'name': "2023 overflow in 2024",
            'company_id': self.env.company.id,
            'date_from': datetime.date(year=2023, month=1, day=1),
            'date_to': datetime.date(year=2024, month=1, day=1),
            'periodicity': 'month',
            'type': 'target',
            'user_type': 'person',
            'commission_amount': 2500,
            'user_ids': [Command.create({
                'user_id': self.commission_user_1.id,
            })],
        })
        self.assertEqual(commission_2023_overflow.user_ids.other_plans, commission_full_year)
        commission_2023_normal = self.env['sale.commission.plan'].create({
            'name': "2023 normal",
            'company_id': self.env.company.id,
            'date_from': datetime.date(year=2023, month=1, day=1),
            'date_to': datetime.date(year=2023, month=12, day=31),
            'periodicity': 'month',
            'type': 'target',
            'user_type': 'person',
            'commission_amount': 2500,
            'user_ids': [Command.create({
                'user_id': self.commission_user_1.id,
            })],
        })
        self.assertEqual(commission_2023_normal.user_ids.other_plans, commission_2023_overflow)
