# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestHrCommon(common.TransactionCase):

    def setUp(self):
        super(TestHrCommon, self).setUp()

        self._quick_create_ctx = {
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_notrack': True,
        }
        self._quick_create_user_ctx = dict(self._quick_create_ctx, no_reset_password=True)

        self.res_users_hr_officer = self.env['res.users'].with_context(self._quick_create_user_ctx).create({
            'name': 'HR Officer',
            'login': 'hro',
            'email': 'hro@example.com',
            'company_id': self.ref('base.main_company'),
            'groups_id': [(6, 0, [self.ref('base.group_user'), self.ref('hr.group_hr_user')])]
        })
