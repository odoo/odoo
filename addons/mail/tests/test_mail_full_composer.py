# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged, HttpCase
from odoo import Command


@tagged('-at_install', 'post_install', 'mail_composer')
class TestMailFullComposer(HttpCase):

    def test_full_composer_tour(self):
        import unittest; raise unittest.SkipTest("skipWOWL")
        self.env['mail.template'].create({
            'name': 'Test template',
            'partner_to': '{{ object.id }}',
            'lang': '{{ object.lang }}',
            'auto_delete': True,
            'model_id': self.ref('base.model_res_partner'),
        })
        testuser = self.env['res.users'].create({
            'email': 'testuser@testuser.com',
            'groups_id': [Command.set([self.ref('base.group_user'), self.ref('base.group_partner_manager')])],
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })
        self.start_tour("/web#id=%d&model=res.partner" % testuser.partner_id, 'mail/static/tests/tours/mail_full_composer_test_tour.js', login='testuser')
