# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged, TransactionCase, Form
from odoo.tools import mute_logger

from unittest.mock import patch

@tagged('post_install', '-at_install')
class TestLoyalty(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.program = cls.env['loyalty.program'].create({
            'name': 'Test Program',
            'reward_ids': [(0, 0, {})],
        })
        cls.product = cls.env['product.product'].with_context(default_taxes_id=False).create({
            'name': "Test Product",
            'detailed_type': 'consu',
            'list_price': 20.0,
        })

    def test_discount_product_unlink(self):
        # Test that we can not unlink dicount line product id
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                with self.cr.savepoint():
                    self.program.reward_ids.discount_line_product_id.unlink()

    def test_loyalty_mail(self):
        # Test basic loyalty_mail functionalities
        loyalty_card_model_id = self.env.ref('loyalty.model_loyalty_card')
        create_tmpl, fifty_tmpl, hundred_tmpl = self.env['mail.template'].create([
            {
                'name': 'CREATE',
                'model_id': loyalty_card_model_id.id,
            },
            {
                'name': '50 points',
                'model_id': loyalty_card_model_id.id,
            },
            {
                'name': '100 points',
                'model_id': loyalty_card_model_id.id,
            },
        ])
        self.program.write({'communication_plan_ids': [
            (0, 0, {
                'program_id': self.program.id,
                'trigger': 'create',
                'mail_template_id': create_tmpl.id,
            }),
            (0, 0, {
                'program_id': self.program.id,
                'trigger': 'points_reach',
                'points': 50,
                'mail_template_id': fifty_tmpl.id,
            }),
            (0, 0, {
                'program_id': self.program.id,
                'trigger': 'points_reach',
                'points': 100,
                'mail_template_id': hundred_tmpl.id,
            }),
        ]})

        sent_mails = self.env['mail.template']

        def mock_send_mail(self, *args, **kwargs):
            nonlocal sent_mails
            sent_mails |= self

        partner = self.env['res.partner'].create({'name': 'Test Partner'})
        with patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail', new=mock_send_mail):
            # Send mail at creation
            coupon = self.env['loyalty.card'].create({
                'program_id': self.program.id,
                'partner_id': partner.id,
                'points': 0,
            })
            self.assertEqual(sent_mails, create_tmpl)
            sent_mails = self.env['mail.template']
            # 50 points mail
            coupon.points = 50
            self.assertEqual(sent_mails, fifty_tmpl)
            sent_mails = self.env['mail.template']
            # Check that it does not get sent again
            coupon.points = 99
            self.assertFalse(sent_mails)
            # 100 points mail
            coupon.points = 100
            self.assertEqual(sent_mails, hundred_tmpl)
            sent_mails = self.env['mail.template']
            # Reset and go straight to 100 points
            coupon.points = 0
            self.assertFalse(sent_mails)
            coupon.points = 100
            self.assertEqual(sent_mails, hundred_tmpl)

    def test_loyalty_program_preserve_reward_upon_writing(self):
        self.program.program_type = 'buy_x_get_y'
        # recompute of rewards
        self.program.flush_recordset(['reward_ids'])

        self.program.write({
            'reward_ids': [
                Command.create({
                    'description': 'Test Product',
                }),
            ],
        })
        self.assertTrue(all(r.reward_type == 'product' for r in self.program.reward_ids))

    def test_loyalty_program_preserve_reward_with_always_edit(self):
        with Form(self.env['loyalty.program']) as program_form:
            program_form.name = 'Test'
            program_form.program_type = 'buy_x_get_y'
            program_form.reward_ids.remove(0)
            with program_form.reward_ids.new() as new_reward:
                new_reward.reward_product_qty = 2
            program = program_form.save()
            self.assertEqual(program.reward_ids.reward_type, 'product')
            self.assertEqual(program.reward_ids.reward_product_qty, 2)

    def test_archiving_unarchiving(self):
        self.program.write({
            'reward_ids': [
                Command.create({
                    'description': 'Test Product',
                }),
            ],
        })
        before_archived_reward_ids = self.program.reward_ids
        self.program.toggle_active()
        self.program.toggle_active()
        after_archived_reward_ids = self.program.reward_ids
        self.assertEqual(before_archived_reward_ids, after_archived_reward_ids)

    def test_prevent_archive_pricelist_linked_to_program(self):
        self.program.pricelist_ids = demo_pricelist = self.env['product.pricelist'].create({
            'name': "Demo"
        })
        with self.assertRaises(UserError):
            demo_pricelist.action_archive()
        self.program.action_archive()
        demo_pricelist.action_archive()

    def test_prevent_archiving_product_linked_to_active_loyalty_reward(self):
        self.program.program_type = 'promotion'
        self.program.flush_recordset()
        product = self.product
        reward = self.env['loyalty.reward'].create({
            'program_id': self.program.id,
            'discount_line_product_id': product.id,
        })
        self.program.write({
            'reward_ids': [Command.link(reward.id)],
        })
        with self.assertRaises(ValidationError):
            product.action_archive()
        self.program.action_archive()
        product.action_archive()

    def test_prevent_archiving_product_used_for_discount_reward(self):
        self.program.program_type = 'promotion'
        self.program.write({
            'reward_ids': [Command.create({
                'discount': 50.0,
                'discount_applicability': 'specific',
                'discount_product_ids': self.product.ids,
            })],
        })
        with self.assertRaises(ValidationError):
            self.product.action_archive()
        self.program.action_archive()
        self.product.action_archive()

    def test_prevent_archiving_product_when_archiving_program(self):
        """
        Test prevent archiving a product when archiving a "Buy X Get Y" program.
        We just have to archive the free product that has been created while creating
        the program itself not the product we already had before.
        """
        product = self.product
        loyalty_program = self.env['loyalty.program'].create({
            'name': 'Test Program',
            'program_type': 'buy_x_get_y',
            'reward_ids': [
                Command.create({
                    'description': 'Test Product',
                    'reward_product_id': product.id,
                    'reward_type': 'product'
                }),
            ],
        })
        loyalty_program.action_archive()
        # Make sure that the main product didn't get archived
        self.assertTrue(product.active)

    def test_card_description_on_tag_change(self):
        product_tag = self.env['product.tag'].create({'name': 'Multiple Products'})
        product1 = self.product
        product1.product_tag_ids = product_tag
        self.env['product.product'].create({
            'name': 'Test Product 2',
            'detailed_type': 'consu',
            'list_price': 30.0,
            'product_tag_ids': product_tag,
        })
        reward = self.env['loyalty.reward'].create({
            'program_id': self.program.id,
            'reward_type': 'product',
            'reward_product_id': product1.id,
        })
        reward_description_single_product = reward.description
        reward.reward_product_tag_id = product_tag
        reward_description_product_tag = reward.description
        self.assertNotEqual(
            reward_description_single_product,
            reward_description_product_tag,
            "Reward description should be changed after adding a tag"
        )
        self.assertEqual(
            reward_description_product_tag,
            "Free Product - [Test Product, Test Product 2]",
            "Reward description for reward with tag should be 'Free Product - [Test Product, Test Product 2]'"
        )
