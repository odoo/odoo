# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests.common import users
from odoo.addons.test_mass_mailing.tests import common
from odoo.addons.test_mass_mailing.models.mass_mail_test import MassMailTestBlacklist
from odoo.exceptions import AccessError, UserError


class TestBLMixin(common.MassMailingCase):

    @classmethod
    def setUpClass(cls):
        super(TestBLMixin, cls).setUpClass()

        cls.env['mail.blacklist'].create([{
            'email': 'Arya.Stark@example.com',
            'active': True,
        }, {
            'email': 'Sansa.Stark@example.com',
            'active': False,
        }])

    @users('emp')
    def test_bl_mixin_primary_field_consistency(self):
        MassMailTestBlacklist._primary_email = ['not_a_field']
        with self.assertRaises(UserError):
            self.env['mass.mail.test.bl'].search([('is_blacklisted', '=', False)])

        MassMailTestBlacklist._primary_email = 'not_a_list'
        with self.assertRaises(UserError):
            self.env['mass.mail.test.bl'].search([('is_blacklisted', '=', False)])

        MassMailTestBlacklist._primary_email = 'email_from'
        with self.assertRaises(UserError):
            self.env['mass.mail.test.bl'].search([('is_blacklisted', '=', False)])

        MassMailTestBlacklist._primary_email = ['email_from', 'name']
        with self.assertRaises(UserError):
            self.env['mass.mail.test.bl'].search([('is_blacklisted', '=', False)])

        MassMailTestBlacklist._primary_email = ['email_from']
        self.env['mass.mail.test.bl'].search([('is_blacklisted', '=', False)])

    @users('emp')
    def test_bl_mixin_is_blacklisted(self):
        """ Test is_blacklisted field computation """
        record = self.env['mass.mail.test.bl'].create({'email_from': 'arya.stark@example.com'})
        self.assertTrue(record.is_blacklisted)

        record = self.env['mass.mail.test.bl'].create({'email_from': 'not.arya.stark@example.com'})
        self.assertFalse(record.is_blacklisted)

    @users('emp')
    def test_bl_mixin_search_blacklisted(self):
        """ Test is_blacklisted field search implementation """
        record1 = self.env['mass.mail.test.bl'].create({'email_from': 'arya.stark@example.com'})
        record2 = self.env['mass.mail.test.bl'].create({'email_from': 'not.arya.stark@example.com'})

        search_res = self.env['mass.mail.test.bl'].search([('is_blacklisted', '=', False)])
        self.assertEqual(search_res, record2)

        search_res = self.env['mass.mail.test.bl'].search([('is_blacklisted', '!=', True)])
        self.assertEqual(search_res, record2)

        search_res = self.env['mass.mail.test.bl'].search([('is_blacklisted', '=', True)])
        self.assertEqual(search_res, record1)

        search_res = self.env['mass.mail.test.bl'].search([('is_blacklisted', '!=', False)])
        self.assertEqual(search_res, record1)

    @users('emp')
    def test_bl_mixin_search_blacklisted_format(self):
        """ Test is_blacklisted field search using email parsing """
        record1 = self.env['mass.mail.test.bl'].create({'email_from': 'Arya Stark <arya.stark@example.com>'})
        self.assertTrue(record1.is_blacklisted)

        search_res = self.env['mass.mail.test.bl'].search([('is_blacklisted', '=', True)])
        self.assertEqual(search_res, record1)
