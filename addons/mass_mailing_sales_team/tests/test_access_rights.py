# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestAccessRights(common.TransactionCase):

    def setUp(self):
        super(TestAccessRights, self).setUp()

        Users = self.env['res.users'].with_context(no_reset_password=True)
        Partners = self.env['res.partner'].with_context(no_reset_password=True)

        group_user = self.env.ref('sales_team.group_sale_manager')

        # Clear blacklist
        blacklist = self.env['mail.mass_mailing.blacklist'].sudo().search([])
        i = len(blacklist)
        while i != 0:
            blacklist[i-1].sudo().unlink()
            i -= 1

        # Create users
        self.user_sales_manager = Users.create({
            'name': 'Andrew Manager',
            'login': 'manager',
            'email': 'a.m@example.com',
            'groups_id': [(6, 0, [group_user.id])]
        })
        self.partner_blacklisted = Partners.create({
            'name': 'Mr Black',
            'email': 'test@black.list'
        })

        # Create a blacklist entry
        self.blacklist_entry = self.env['mail.mass_mailing.blacklist'].create({
            'email': 'test@black.list',
        })

    def test_access_sales_manager(self):
        """ Test sales manager's access rights """
        # sale manager can see a blacklist entry
        self.blacklist_entry.sudo(self.user_sales_manager).read()
        # sale manager can edit a blacklist entry
        self.blacklist_entry.sudo(self.user_sales_manager).write({'name': 'test'})
        # sale manager create a blacklist entry
        self.env['mail.mass_mailing.blacklist'].sudo(self.user_sales_manager).create({
            'email': 'another@black.list',
        })
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 2)
        # sale manager can delete a blacklist entry
        self.blacklist_entry.sudo(self.user_sales_manager).unlink()
        self.assertTrue(len(self.env['mail.mass_mailing.blacklist'].search([])) == 1)

        # sale manager can see if user is balcklisted using mixin
        self.assertFalse(self.partner_blacklisted.sudo(self.user_sales_manager).is_blacklisted)
        # sale manager can add the blacklisted user to the blacklist using the mixin
        self.partner_blacklisted.sudo(self.user_sales_manager).toggle_blacklist()
        self.assertTrue(self.partner_blacklisted.sudo(self.user_sales_manager).is_blacklisted)
        # sale manager can remove the blacklisted user from the blacklist using the mixin
        self.partner_blacklisted.sudo(self.user_sales_manager).toggle_blacklist()
        self.assertFalse(self.partner_blacklisted.sudo(self.user_sales_manager).is_blacklisted)