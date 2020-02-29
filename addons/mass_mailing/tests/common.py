# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCase, mail_new_test_user
from odoo.tests.common import SavepointCase


class TestMassMailCommon(SavepointCase, MailCase):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailCommon, cls).setUpClass()

        cls.user_marketing = mail_new_test_user(
            cls.env, login='user_marketing',
            groups='base.group_user,base.group_partner_manager,mass_mailing.group_mass_mailing_user',
            name='Martial Marketing', signature='--\nMartial')

        cls.mailing_list_1 = cls.env['mailing.list'].create({
            'name': 'List1',
            'contact_ids': [
                (0, 0, {'name': 'Déboulonneur', 'email': 'fleurus@example.com'}),
                (0, 0, {'name': 'Gorramts', 'email': 'gorramts@example.com'}),
                (0, 0, {'name': 'Ybrant', 'email': 'ybrant@example.com'}),
            ]
        })
        cls.mailing_list_2 = cls.env['mailing.list'].create({
            'name': 'List2',
            'contact_ids': [
                (0, 0, {'name': 'Gilberte', 'email': 'gilberte@example.com'}),
                (0, 0, {'name': 'Gilberte En Mieux', 'email': 'gilberte@example.com'}),
                (0, 0, {'name': 'Norbert', 'email': 'norbert@example.com'}),
                (0, 0, {'name': 'Ybrant', 'email': 'ybrant@example.com'}),
            ]
        })

        cls.email_reply_to = 'MyCompany SomehowAlias <test.alias@test.mycompany.com>'
