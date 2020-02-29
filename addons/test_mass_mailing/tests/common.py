# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.tests import common


class TestMailCommon(common.TestMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailCommon, cls).setUpClass()

        cls.user_marketing = mail_new_test_user(
            cls.env, login='marketing',
            groups='base.group_user,base.group_partner_manager,mass_mailing.group_mass_mailing_user',
            name='Martial Marketing', signature='--\nMartial')
