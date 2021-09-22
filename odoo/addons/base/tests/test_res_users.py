# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, Form, tagged


class TestUsers(TransactionCase):

    def test_name_search(self):
        """ Check name_search on user. """
        User = self.env['res.users']

        test_user = User.create({'name': 'Flad the Impaler', 'login': 'vlad'})
        like_user = User.create({'name': 'Wlad the Impaler', 'login': 'vladi'})
        other_user = User.create({'name': 'Nothing similar', 'login': 'nothing similar'})
        all_users = test_user | like_user | other_user

        res = User.name_search('vlad', operator='ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, test_user)

        res = User.name_search('vlad', operator='not ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, all_users)

        res = User.name_search('', operator='ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, all_users)

        res = User.name_search('', operator='not ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, User)

        res = User.name_search('lad', operator='ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, test_user | like_user)

        res = User.name_search('lad', operator='not ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, other_user)

    def test_user_partner(self):
        """ Check that the user partner is well created """

        User = self.env['res.users']
        Partner = self.env['res.partner']
        Company = self.env['res.company']

        company_1 = Company.create({'name': 'company_1'})
        company_2 = Company.create({'name': 'company_2'})

        partner = Partner.create({
            'name': 'Bob Partner',
            'company_id': company_2.id
        })

        # case 1 : the user has no partner
        test_user = User.create({
            'name': 'John Smith',
            'login': 'jsmith',
            'company_ids': [company_1.id],
            'company_id': company_1.id
        })

        self.assertFalse(
            test_user.partner_id.company_id,
            "The partner_id linked to a user should be created without any company_id")

        # case 2 : the user has a partner
        test_user = User.create({
            'name': 'Bob Smith',
            'login': 'bsmith',
            'company_ids': [company_1.id],
            'company_id': company_1.id,
            'partner_id': partner.id
        })

        self.assertEqual(
            test_user.partner_id.company_id,
            company_1,
            "If the partner_id of a user has already a company, it is replaced by the user company"
        )


    def test_change_user_company(self):
        """ Check the partner company update when the user company is changed """

        User = self.env['res.users']
        Company = self.env['res.company']

        test_user = User.create({'name': 'John Smith', 'login': 'jsmith'})
        company_1 = Company.create({'name': 'company_1'})
        company_2 = Company.create({'name': 'company_2'})

        test_user.company_ids += company_1
        test_user.company_ids += company_2

        # 1: the partner has no company_id, no modification
        test_user.write({
            'company_id': company_1.id
        })

        self.assertFalse(
            test_user.partner_id.company_id,
            "On user company change, if its partner_id has no company_id,"
            "the company_id of the partner_id shall NOT be updated")

        # 2: the partner has a company_id different from the new one, update it
        test_user.partner_id.write({
            'company_id': company_1.id
        })

        test_user.write({
            'company_id': company_2.id
        })

        self.assertEqual(
            test_user.partner_id.company_id,
            company_2,
            "On user company change, if its partner_id has already a company_id,"
            "the company_id of the partner_id shall be updated"
        )

@tagged('post_install', '-at_install')
class TestUsers2(TransactionCase):
    def test_reified_groups(self):
        """ The groups handler doesn't use the "real" view with pseudo-fields
        during installation, so it always works (because it uses the normal
        groups_id field).
        """
        # use the specific views which has the pseudo-fields
        f = Form(self.env['res.users'], view='base.view_users_form')
        f.name = "bob"
        f.login = "bob"
        user = f.save()

        self.assertIn(self.env.ref('base.group_user'), user.groups_id)
