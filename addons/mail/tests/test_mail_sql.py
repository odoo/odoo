# -*- coding: utf-8 -*-

from odoo import sql_db
from odoo.tests.common import TransactionCase
from odoo.tools import enable_logger


class TestMailProut(TransactionCase):

    def setUp(self):
        super(TestMailProut, self).setUp()
        self.user_employee = self.env['res.users'].with_context({
            'no_reset_password': True,
            'mail_create_nosubscribe': True
        }).create({
            'name': 'Ernest Employee',
            'login': 'ernest',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })

        # self.test_record = self.env['mail.test'].create({
        #     'name': 'Test'
        # })

    # @enable_logger('odoo.sql_db.bob')
    # def test_sql_message_post(self):
    #     print '--------------------------------------------------------'
    #     print '--------------------------------------------------------'
    #     self.test_record.sudo(self.user_employee).message_post(
    #         body='Test Body')
    #     print '--------------------------------------------------------'
    #     print '--------------------------------------------------------'

    @enable_logger('odoo.sql_db.bob')
    def test_simple(self):
        print '--------------------------------------------------------'
        print '--------------------------------------------------------'
        zboobs = self.env['mail.test'].sudo(self.user_employee).create({'name': 'Zboobs'})
        print '--------------------------------------------------------'
        print '--------------------------------------------------------'
