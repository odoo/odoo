# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestPartner(TransactionCase):

    def test_name_search(self):
        """ Check name_search on partner, especially with domain based on auto_join
        user_ids field. Check specific SQL of name_search correctly handle joined tables. """
        test_partner = self.env['res.partner'].create({'name': 'Vlad the Impaler'})
        test_user = self.env['res.users'].create({'name': 'Vlad the Impaler', 'login': 'vlad', 'email': 'vlad.the.impaler@example.com'})

        ns_res = self.env['res.partner'].name_search('Vlad', operator='ilike')
        self.assertEqual(set(i[0] for i in ns_res), set((test_partner | test_user.partner_id).ids))

        ns_res = self.env['res.partner'].name_search('Vlad', args=[('user_ids.email', 'ilike', 'vlad')])
        self.assertEqual(set(i[0] for i in ns_res), set(test_user.partner_id.ids))

    def test_company_change_propagation(self):
        """ Check propagation of company_id across children """
        User = self.env['res.users']
        Partner = self.env['res.partner']
        Company = self.env['res.company']

        company_1 = Company.create({'name': 'company_1'})
        company_2 = Company.create({'name': 'company_2'})

        test_partner_company = Partner.create({'name': 'This company'})
        test_user = User.create({'name': 'This user', 'login': 'thisu', 'email': 'this.user@example.com', 'company_id': company_1.id, 'company_ids': [company_1.id]})
        test_user.partner_id.write({'parent_id': test_partner_company.id})

        test_partner_company.write({'company_id': company_1.id})
        self.assertEqual(test_user.partner_id.company_id.id, company_1.id, "The new company_id of the partner company should be propagated to its children")

        test_partner_company.write({'company_id': False})
        self.assertFalse(test_user.partner_id.company_id.id, "If the company_id is deleted from the partner company, it should be propagated to its children")

        with self.assertRaises(UserError, msg="You should not be able to update the company_id of the partner company if the linked user of a child partner is not an allowed to be assigned to that company"), self.cr.savepoint():
            test_partner_company.write({'company_id': company_2.id})
