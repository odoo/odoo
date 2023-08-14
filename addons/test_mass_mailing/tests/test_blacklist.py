# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import users
from odoo.addons.test_mass_mailing.tests import common
from odoo.exceptions import AccessError


class TestBLAccessRights(common.TestMassMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestBLAccessRights, cls).setUpClass()
        cls._create_portal_user()

        cls.bl_rec = cls.env['mail.blacklist'].create([
            {'email': 'Not A Stark <john.snow@example.com>'},
        ])
        cls.bl_previous = cls.env['mail.blacklist'].search([])

    @users('employee')
    def test_bl_crud_employee(self):
        with self.assertRaises(AccessError):
            self.env['mail.blacklist'].create([{'email': 'Arya.Stark@example.com'}])

        with self.assertRaises(AccessError):
            self.bl_rec.with_user(self.env.user).read([])

        with self.assertRaises(AccessError):
            self.bl_rec.with_user(self.env.user).write({'email': 'jaimie.lannister@example.com'})

        with self.assertRaises(AccessError):
            self.bl_rec.with_user(self.env.user).unlink()

    @users('portal_test')
    def test_bl_crud_portal(self):
        with self.assertRaises(AccessError):
            self.env['mail.blacklist'].create([{'email': 'Arya.Stark@example.com'}])

        with self.assertRaises(AccessError):
            self.bl_rec.with_user(self.env.user).read([])

        with self.assertRaises(AccessError):
            self.bl_rec.with_user(self.env.user).write({'email': 'jaimie.lannister@example.com'})

        with self.assertRaises(AccessError):
            self.bl_rec.with_user(self.env.user).unlink()

    @users('user_marketing')
    def test_bl_crud_marketing(self):
        self.env['mail.blacklist'].create([{'email': 'Arya.Stark@example.com'}])

        read_res = self.bl_rec.with_user(self.env.user).read([])
        self.assertEqual(read_res[0]['id'], self.bl_rec.id)

        self.bl_rec.with_user(self.env.user).write({'email': 'jaimie.lannister@example.com'})
        self.assertEqual(self.bl_rec.email, 'jaimie.lannister@example.com')

        self.bl_rec.with_user(self.env.user).unlink()


class TestBLConsistency(common.TestMassMailCommon):
    _base_list = ['Arya.Stark@example.com', 'ned.stark@example.com']

    def setUp(self):
        super(TestBLConsistency, self).setUp()
        self.bl_rec = self.env['mail.blacklist'].create([
            {'email': 'Not A Stark <john.snow@example.com>'},
        ])

        self.bl_previous = self.env['mail.blacklist'].search([])

    @users('user_marketing')
    def test_bl_check_case_add(self):
        """ Test emails case when adding through _add """
        bl_sudo = self.env['mail.blacklist'].sudo()
        existing = bl_sudo.create({
            'email': 'arya.stark@example.com',
            'active': False,
        })

        added = self.env['mail.blacklist']._add('Arya.Stark@EXAMPLE.com')
        self.assertEqual(existing, added)
        self.assertTrue(existing.active)

    @users('user_marketing')
    def test_bl_check_case_remove(self):
        """ Test emails case when deactivating through _remove """
        bl_sudo = self.env['mail.blacklist'].sudo()
        existing = bl_sudo.create({
            'email': 'arya.stark@example.com',
            'active': True,
        })

        added = self.env['mail.blacklist']._remove('Arya.Stark@EXAMPLE.com')
        self.assertEqual(existing, added)
        self.assertFalse(existing.active)

    @users('user_marketing')
    def test_bl_create_duplicate(self):
        """ Test emails are inserted only once if duplicated """
        bl_sudo = self.env['mail.blacklist'].sudo()
        self.env['mail.blacklist'].create([
            {'email': self._base_list[0]},
            {'email': self._base_list[1]},
            {'email': 'Another Ned Stark <%s>' % self._base_list[1]},
        ])

        new_bl = bl_sudo.search([('id', 'not in', self.bl_previous.ids)])

        self.assertEqual(len(new_bl), 2)
        self.assertEqual(
            set(v.lower() for v in self._base_list),
            set(v.lower() for v in new_bl.mapped('email'))
        )

    @users('user_marketing')
    def test_bl_create_parsing(self):
        """ Test email is correctly extracted from given entries """
        bl_sudo = self.env['mail.blacklist'].sudo()
        self.env['mail.blacklist'].create([
            {'email': self._base_list[0]},
            {'email': self._base_list[1]},
            {'email': 'Not Ned Stark <jaimie.lannister@example.com>'},
        ])

        new_bl = bl_sudo.search([('id', 'not in', self.bl_previous.ids)])

        self.assertEqual(len(new_bl), 3)
        self.assertEqual(
            set(v.lower() for v in self._base_list + ['jaimie.lannister@example.com']),
            set(v.lower() for v in new_bl.mapped('email'))
        )

    @users('user_marketing')
    def test_bl_search_exact(self):
        search_res = self.env['mail.blacklist'].search([('email', '=', 'john.snow@example.com')])
        self.assertEqual(search_res, self.bl_rec)

    @users('user_marketing')
    def test_bl_search_parsing(self):
        search_res = self.env['mail.blacklist'].search([('email', '=', 'Not A Stark <john.snow@example.com>')])

        self.assertEqual(search_res, self.bl_rec)

        search_res = self.env['mail.blacklist'].search([('email', '=', '"John J. Snow" <john.snow@example.com>')])
        self.assertEqual(search_res, self.bl_rec)

        search_res = self.env['mail.blacklist'].search([('email', '=', 'Aegon? <john.snow@example.com>')])
        self.assertEqual(search_res, self.bl_rec)

        search_res = self.env['mail.blacklist'].search([('email', '=', '"John; \"You know Nothing\" Snow" <john.snow@example.com>')])
        self.assertEqual(search_res, self.bl_rec)

    @users('user_marketing')
    def test_bl_search_case(self):
        search_res = self.env['mail.blacklist'].search([('email', '=', 'john.SNOW@example.COM>')])
        self.assertEqual(search_res, self.bl_rec)

    @users('user_marketing')
    def test_bl_search_partial(self):
        search_res = self.env['mail.blacklist'].search([('email', 'ilike', 'John')])
        self.assertEqual(search_res, self.bl_rec)
        search_res = self.env['mail.blacklist'].search([('email', 'ilike', 'n.SNOW@example.cO>')])
        self.assertEqual(search_res, self.bl_rec)
