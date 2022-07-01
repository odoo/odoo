# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged, HttpCase


@tagged('-at_install', 'post_install', 'mail_composer')
class TestMailFullComposer(HttpCase):

    def test_full_composer_tour(self):
        import unittest; raise unittest.SkipTest("skipWOWL")
        self.env['mail.template'].create({
            'name': 'Test template',  # name hardcoded for test
            'partner_to': '${object.id}',
            'lang': '${object.lang}',
            'auto_delete': True,
            'model_id': self.ref('base.model_res_partner'),
        })
        test_user = self.env['res.users'].create({
            'email': 'testuser@testuser.com',
            'groups_id': [
                (6, 0, [self.ref('base.group_user'), self.ref('base.group_partner_manager')]),
            ],
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })

        automated_action = self.env['base.automation'].create({
            'name': 'Test',
            'active': True,
            'trigger': 'on_change',
            'on_change_field_ids': (4, self.ref('mail.field_mail_compose_message__template_id'),),
            'state': 'code',
            'model_id': self.env.ref('mail.model_mail_compose_message').id,
        })

        self.start_tour("/web#id=%d&model=res.partner" % test_user.partner_id, 'mail/static/tests/tours/mail_full_composer_test_tour.js', login='testuser')

        automated_action.unlink()
