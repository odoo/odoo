# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.tests import common


class TestAccessRights(common.TransactionCase):

    def setUp(self):
        super(TestAccessRights, self).setUp()

        Users = self.env['res.users'].with_context(no_reset_password=True)
        Partners = self.env['res.partner'].with_context(no_reset_password=True)
        Mass_Mailing_Contacts = self.env['mail.mass_mailing.contact'].with_context(no_reset_password=True)

        group_user = self.env.ref('mass_mailing.group_mass_mailing_user')

        # Clear blacklist
        blacklist = self.env['mail.mass_mailing.blacklist'].sudo().search([])
        i = len(blacklist)
        while i != 0:
            blacklist[i-1].sudo().unlink()
            i -= 1

        # Create users
        self.user_mm_user = Users.create({
            'name': 'Andrew User',
            'login': 'user',
            'email': 'a.m@example.com',
            'groups_id': [(6, 0, [group_user.id])]
        })
        self.user_employee = Users.create({
            'name': 'Bert Tartignole',
            'login': 'bert',
            'email': 'b.t@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })
        self.user_portal = Users.create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'email': 'chell@gladys.portal',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
        })
        self.contact_blacklisted = Mass_Mailing_Contacts.create({
            'name': 'Jack Black',
            'email': 'contact@black.list'
        })
        self.partner_blacklisted = Partners.create({
            'name': 'Joe Black',
            'email': 'test@black.list'
        })

        # Create a blacklist entry
        self.blacklist_entry = self.env['mail.mass_mailing.blacklist'].create({
            'email': 'test@black.list',
        })
        self.blacklist_contact_entry = self.env['mail.mass_mailing.blacklist'].create({
            'email': 'contact@black.list',
        })

    def test_access_mass_mailing_user(self):
        """ Test Mass Mailing user's access rights """
        # ===================
        # Test on res_partner
        # ===================
        # mass mailing user can see a blacklist entry
        self.blacklist_entry.sudo(self.user_mm_user).read()
        # mass mailing user can edit a blacklist entry
        self.blacklist_entry.sudo(self.user_mm_user).write({'name': 'test'})
        # mass mailing user can create a blacklist entry
        self.env['mail.mass_mailing.blacklist'].sudo(self.user_mm_user).create({
            'email': 'another@black.list',
        })
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 3)
        # mass mailing user can delete a blacklist entry
        self.blacklist_entry.sudo(self.user_mm_user).with_context(caca=True).unlink()
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 2)

        # mass mailing user can see if user is balcklisted using mixin
        self.assertFalse(self.partner_blacklisted.sudo(self.user_mm_user).is_blacklisted)
        # mass mailing user can add the blacklisted user to the blacklist using the mixin
        self.partner_blacklisted.sudo(self.user_mm_user).toggle_blacklist()
        self.assertTrue(self.partner_blacklisted.sudo(self.user_mm_user).is_blacklisted)
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 3)
        # mass mailing user can remove the blacklisted user from the blacklist using the mixin
        self.partner_blacklisted.sudo(self.user_mm_user).toggle_blacklist()
        self.assertFalse(self.partner_blacklisted.sudo(self.user_mm_user).is_blacklisted)
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 2)

        # ============================
        # Test on mass mailing contact
        # ============================
        self.blacklist_contact_entry.sudo(self.user_mm_user).read()
        self.blacklist_contact_entry.sudo(self.user_mm_user).write({'name': 'test'})
        self.env['mail.mass_mailing.blacklist'].sudo(self.user_mm_user).create({
            'email': 'again_another@black.list',
        })
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 3)
        self.blacklist_contact_entry.sudo(self.user_mm_user).unlink()
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 2)

        self.assertFalse(self.contact_blacklisted.sudo(self.user_mm_user).is_blacklisted)
        self.contact_blacklisted.sudo(self.user_mm_user).toggle_blacklist()
        self.assertTrue(self.contact_blacklisted.sudo(self.user_mm_user).is_blacklisted)
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 3)
        self.contact_blacklisted.sudo(self.user_mm_user).toggle_blacklist()
        self.assertFalse(self.contact_blacklisted.sudo(self.user_mm_user).is_blacklisted)
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 2)


    def test_access_portal_user(self):
        """ Test portal user's access rights """
        # Portal user can't see blacklist entries
        with self.assertRaises(AccessError):
            self.blacklist_entry.sudo(self.user_portal).read()
        # Portal user can't edit a blacklist entry
        with self.assertRaises(AccessError):
            self.blacklist_entry.sudo(self.user_portal).write({'name': 'test'})
        # Portal user can't create a blacklist entry
        with self.assertRaises(AccessError):
            self.env['mail.mass_mailing.blacklist'].sudo(self.user_portal).create({
                'email': 'another@black.list',
            })
        # Portal user can't delete a blacklist entry
        with self.assertRaises(AccessError):
            self.blacklist_entry.sudo(self.user_portal).unlink()

        # Portal user can't see if user is balcklisted using mixin
        with self.assertRaises(AccessError):
            self.partner_blacklisted.sudo(self.user_portal).is_blacklisted()
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 2)
        # Portal user can't remove or add the blacklisted user from the blacklist using the mixin
        with self.assertRaises(AccessError):
            self.partner_blacklisted.sudo(self.user_portal).toggle_blacklist()
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 2)


    def test_access_employee(self):
        """ Test classic employee's access rights """
        # Employee can't see blacklist entries
        with self.assertRaises(AccessError):
            self.blacklist_entry.sudo(self.user_employee).read()
        # Employee can't edit a blacklist entry
        with self.assertRaises(AccessError):
            self.blacklist_entry.sudo(self.user_employee).write({'name': 'test'})
        # Employee can't create a blacklist entry
        with self.assertRaises(AccessError):
            self.env['mail.mass_mailing.blacklist'].sudo(self.user_employee).create({
                'email': 'another@black.list',
            })
        # Employee can't delete a blacklist entry
        with self.assertRaises(AccessError):
            self.blacklist_entry.sudo(self.user_employee).unlink()

        # Employee can see if user is balcklisted using mixin
        self.assertTrue(self.partner_blacklisted.sudo(self.user_employee).is_blacklisted)
        # Employee can remove the blacklisted user from the blacklist using the mixin
        self.partner_blacklisted.sudo(self.user_employee).toggle_blacklist()
        self.assertFalse(self.partner_blacklisted.sudo(self.user_employee).is_blacklisted)
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 1)
        # Employee can add the blacklisted user to the blacklist using the mixin
        self.partner_blacklisted.sudo(self.user_employee).toggle_blacklist()
        self.assertTrue(self.partner_blacklisted.sudo(self.user_employee).is_blacklisted)
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 2)
