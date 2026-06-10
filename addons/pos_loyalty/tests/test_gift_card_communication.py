# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestGiftCardCommunication(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.mail_template = cls.env['mail.template'].create({
            'name': 'Test Gift Card Email',
            'model_id': cls.env.ref('loyalty.model_loyalty_card').id,
            'subject': 'Your Gift Card',
            'body_html': '<p>Here is your gift card: {{ object.code }}</p>',
        })

        # Create a gift card program
        cls.gift_card_program = cls.env['loyalty.program'].create({
            'name': 'Test Gift Card Program',
            'program_type': 'gift_card',
            'applies_on': 'future',
            'trigger': 'auto',
            'rule_ids': [Command.create({
                'reward_point_mode': 'money',
                'reward_point_amount': 1,
                'product_ids': cls.env.ref('loyalty.gift_card_product_50'),
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 1,
                'discount_applicability': 'order',
                'required_points': 1,
            })],
            'trigger_product_ids': cls.env.ref('loyalty.gift_card_product_50'),
            'mail_template_id': cls.mail_template.id,
            'pos_report_print_id': cls.env.ref('loyalty.report_gift_card').id,
        })

        cls.test_partner = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test.customer@example.com',
        })

    def test_gift_card_email_logged_to_pos_order_chatter(self):
        """
        Test that when a gift card is created and an email is sent,
        the email content is logged to the pos.order's chatter.
        """
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        self.main_pos_config.open_ui()
        self.start_pos_tour('test_gift_card_email_logged_to_pos_order_chatter')

        pos_order = self.main_pos_config.current_session_id.order_ids[0]
        gift_card = self.env['loyalty.card'].search([
            ('code', '=', 'TEST-GIFT-CARD-001'),
        ], limit=1)

        self.assertTrue(gift_card.exists(), "Gift card should be created")
        self.assertEqual(
            gift_card.program_id.program_type, 'gift_card',
            "Card should be a gift card",
        )
        self.assertEqual(
            gift_card.source_pos_order_id.id, pos_order.id,
            "Gift card should reference the POS order",
        )

        mail = self.env['mail.mail'].search([
            ('model', '=', 'loyalty.card'),
            ('res_id', '=', gift_card.id),
        ], order='id desc', limit=1)

        self.assertTrue(mail.exists(), "An email should be created for the gift card")

        messages_after = len(pos_order.message_ids)
        self.assertGreater(messages_after, 0,
                          "A new message should be posted to the POS order")

        last_message = pos_order.message_ids.sorted('id', reverse=True)[0]

        self.assertIn(
            'gift card', last_message.body.lower(),
            "The message should contain gift card information",
        )

    def test_gift_card_email_logged_only_for_gift_cards(self):
        """
        Test that the email logging only happens for gift cards,
        not for other coupon types (loyalty, ewallet, etc.)
        """
        loyalty_program = self.env['loyalty.program'].create({
            'name': 'Test Loyalty Program',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [Command.create({
                'reward_point_mode': 'money',
                'reward_point_amount': 1,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 10,
            })],
            'mail_template_id': self.mail_template.id,
        })

        self.main_pos_config.open_ui()
        self.start_pos_tour('test_gift_card_email_logged_only_for_gift_cards')

        pos_order = self.main_pos_config.current_session_id.order_ids[0]

        loyalty_card = self.env['loyalty.card'].search([
            ('program_id', '=', loyalty_program.id),
            ('partner_id', '=', self.test_partner.id),
        ], limit=1)

        self.assertTrue(loyalty_card.exists(), "Loyalty card should be created")
        self.assertEqual(
            loyalty_card.program_id.program_type, 'loyalty',
            "Card should be a loyalty card",
        )
        mail = self.env['mail.mail'].search([
            ('model', '=', 'loyalty.card'),
            ('res_id', '=', loyalty_card.id),
        ], order='id desc', limit=1)
        self.assertFalse(mail.exists(), "An email should not be created for the loyalty type program card")
        last_message = pos_order.message_ids.sorted('id', reverse=True)[0]

        self.assertIn(
            'point of sale order created', last_message.body.lower(),
            "The message should contain order creation information",
        )

    def test_gift_card_email_without_customer(self):
        """
        Test that no email is sent and logged when the gift card
        has no customer associated with it.
        """
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        self.main_pos_config.open_ui()
        self.start_pos_tour('test_gift_card_email_without_customer')

        pos_order = self.main_pos_config.current_session_id.order_ids[0]
        gift_card = self.env['loyalty.card'].search([
            ('code', '=', 'TEST-NO-CUSTOMER-001'),
        ])
        self.assertTrue(
            gift_card.exists(), "Gift card should be created even without customer",
        )
        self.assertEqual(
            gift_card.source_pos_order_id.id, pos_order.id,
            "Gift card should reference the POS order",
        )

        mail = self.env['mail.mail'].search([
            ('model', '=', 'loyalty.card'),
            ('res_id', '=', gift_card.id),
        ], order='id desc', limit=1)
        self.assertFalse(mail.exists(), "An email should not be created for the loyalty type program card")
        last_message = pos_order.message_ids.sorted('id', reverse=True)[0]

        self.assertIn(
            'point of sale order created', last_message.body.lower(),
            "The message must only created mail contain order creation information",
        )
