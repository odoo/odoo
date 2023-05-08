# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestImLivechatCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.operators = cls.env['res.users'].create([{
            'name': 'Michel',
            'login': 'michel',
            'livechat_username': "Michel Operator",
            'email': 'michel@example.com',
        }, {
            'name': 'Paul',
            'login': 'paul'
        }, {
            'name': 'Pierre',
            'login': 'pierre'
        }, {
            'name': 'Jean',
            'login': 'jean'
        }, {
            'name': 'Georges',
            'login': 'georges'
        }])

        cls.visitor_user = cls.env['res.users'].create({
            'name': 'Rajesh',
            'login': 'rajesh',
            'country_id': cls.env.ref('base.in').id,
            'email': 'rajesh@example.com',
        })

        cls.livechat_channel = cls.env['im_livechat.channel'].create({
            'name': 'The channel',
            'user_ids': [(6, 0, cls.operators.ids)]
        })

    def setUp(self):
        super().setUp()

        def get_available_users(_):
            return self.operators

        self.patch(type(self.env['im_livechat.channel']), '_get_available_users', get_available_users)
