# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common


class TestHrCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.res_users_hr_officer = mail_new_test_user(
            cls.env,
            email='hro@example.com',
            login='hro',
            groups='base.group_user,hr.group_hr_user,base.group_partner_manager',
            name='HR Officer',
        )
