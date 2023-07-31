# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase


class TestImLivechatCommon(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.password = 'Pl1bhD@2!kXZ'
        cls.operators = cls.env['res.users'].create([{
            'name': 'Michel',
            'login': 'michel',
            'password': cls.password,
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

        def _compute_available_operator_ids(channel_self):
            for record in channel_self:
                record.available_operator_ids = type(self).operators

        self.patch(type(self.env['im_livechat.channel']), '_compute_available_operator_ids', _compute_available_operator_ids)
