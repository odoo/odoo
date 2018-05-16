# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.tests import common


class TestAccessRights(common.TransactionCase):

    def setUp(self):
        super(TestAccessRights, self).setUp()

        Mass_Mailing_Contacts = self.env['mail.mass_mailing.contact'].with_context(no_reset_password=True)

        # Clear blacklist
        blacklist = self.env['mail.mass_mailing.blacklist'].sudo().search([])
        i = len(blacklist)
        while i != 0:
            blacklist[i-1].sudo().unlink()
            i -= 1

        # Create users
        self.contact_blacklisted = Mass_Mailing_Contacts.create({
            'name': 'Jack Black',
            'email': 'contact@black.list'
        })

        # Create a blacklist entry
        self.blacklist_contact_entry = self.env['mail.mass_mailing.blacklist'].create({
            'email': 'contact@black.list',
        })

    def test_blacklist_on_leads(self):
        """ Test on mass mailing contact """
        # ============================
        # Test on mass mailing contact
        # ============================
        self.blacklist_contact_entry.sudo().read()
        self.blacklist_contact_entry.sudo().write({'name': 'test'})
        self.env['mail.mass_mailing.blacklist'].sudo().create({
            'email': 'another@black.list',
        })
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 2)
        self.blacklist_contact_entry.sudo().unlink()
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 1)

        self.assertFalse(self.contact_blacklisted.sudo().is_blacklisted)
        self.contact_blacklisted.sudo().toggle_blacklist()
        self.assertTrue(self.contact_blacklisted.sudo().is_blacklisted)
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 2)
        self.contact_blacklisted.sudo().toggle_blacklist()
        self.assertFalse(self.contact_blacklisted.sudo().is_blacklisted)
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 1)


