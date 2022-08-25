# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

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
