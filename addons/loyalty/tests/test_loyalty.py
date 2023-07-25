# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import tagged, TransactionCase
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

    def test_prevent_archiving_product_linked_to_active_loyalty_reward(self):
        self.program.program_type = 'promotion'
        self.program.flush_recordset()
        product = self.env['product.product'].with_context(default_taxes_id=False).create({
            'name': 'Test Product',
            'detailed_type': 'consu',
            'list_price': 20.0,
        })
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
