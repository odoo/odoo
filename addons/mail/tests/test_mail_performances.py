# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common_performances import queryCount, TestPerformance


class TestMailPerformances(TestPerformance):

    def setUp(self):
        super(TestMailPerformances, self).setUp()
        self.user_employee = self.env['res.users'].with_context({
            'no_reset_password': True,
            'mail_create_nosubscribe': True
        }).create({
            'name': 'Ernest Employee',
            'login': 'emp',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })

        # for performances test
        self.admin = self.env.user
        self.emp = self.user_employee

        self.test_record_activity = self.env['mail.test.activity'].create({'name': 'Zboobs'})
        self.test_record_activity_id = self.test_record_activity.id

    @queryCount(admin=20, emp=26)
    def test_simple(self):
        self.env['mail.test.simple'].create({'name': 'Zboobs'})

    @queryCount(admin=23, emp=29)
    def test_activity(self):
        self.env['mail.test.activity'].create({'name': 'Zboobs'})

    @queryCount(admin=37, emp=42)
    def test_activity_full(self):
        self.env['mail.activity'].with_context({
            'default_res_model': 'mail.test.activity',
        }).create({
            'summary': 'Test Activity',
            'res_id': self.test_record_activity_id,
        })
