# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon
from odoo.tests.common import tagged

@tagged('-at_install', 'post_install')
class TestBuyGiftCard(TestSaleCouponCommon):

    def test_buying_gift_card(self):
        order = self.empty_order
        self.immediate_promotion_program.active = False
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': 'Ordinary Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            (0, False, {
                'product_id': self.product_gift_card.id,
                'name': 'Gift Card Product',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self.assertEqual(len(order.order_line.ids), 2)
        self.assertEqual(len(order._get_reward_coupons()), 0)
        order._update_programs_and_rewards()
        self.assertEqual(len(order._get_reward_coupons()), 1)
        order.order_line[1].product_uom_qty = 2
        order._update_programs_and_rewards()
        self.assertEqual(len(order._get_reward_coupons()), 2)
        order.order_line[1].product_uom_qty = 1
        order._update_programs_and_rewards()
        self.assertEqual(len(order._get_reward_coupons()), 1)

    def test_gift_card_email_sender(self):
        """Ensure that sending gift card emails have a sender.
        Either the order's salesman if available, otherwise the order's company.
        """
        mail_template = self.env['mail.template'].create({
            'name': "Gift Card Mail",
            'model_id': self.env.ref('loyalty.model_loyalty_card').id,
            'auto_delete': False,
        })
        self.program_gift_card.communication_plan_ids = [Command.create({
            'trigger': 'create',
            'mail_template_id': mail_template.id,
        })]
        order = self.empty_order
        salesman = order.user_id.partner_id.ensure_one()
        salesman.email = "sales@company.co"
        company = order.company_id.partner_id
        company.email = "noreply@company.co"
        order.write({
            'order_line': [Command.create({'product_id': self.product_gift_card.id})],
        })
        order._update_programs_and_rewards()

        # Create an order without salesman to test company-based fallback
        orders = order + order.copy({'user_id': None})

        # Clear out the mailbox before sending mail
        self.env['mail.mail'].search([]).sudo().unlink()

        # Confirm order as Public User to trigger loyalty mail
        public_user = self.env.ref('base.public_user')
        orders.with_user(public_user).with_company(order.company_id).sudo().action_confirm()

        mails = self.env['mail.mail'].search([])
        self.assertEqual(len(mails), 2)
        salesman_mail = mails.filtered(lambda m: m.author_id == salesman).ensure_one()
        company_mail = mails.filtered(lambda m: m.author_id == company).ensure_one()
        self.assertEqual(salesman_mail.email_from, salesman.email_formatted)
        self.assertEqual(company_mail.email_from, company.email_formatted)
