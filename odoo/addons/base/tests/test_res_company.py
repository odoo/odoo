# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError, UserError
from odoo.tests.common import TransactionCase


class TestCompany(TransactionCase):

    def test_check_active(self):
        """Tests the ability to archive a company whether or not it still has active users.
        Tests an archived user in an archived company cannot be unarchived
        without changing its company to an active company."""
        company = self.env['res.company'].create({'name': 'foo'})
        user = self.env['res.users'].create({
            'name': 'foo',
            'login': 'foo',
            'company_id': company.id,
            'company_ids': company.ids,
        })

        # The company cannot be archived because it still has active users
        with self.assertRaisesRegex(ValidationError, 'The company foo cannot be archived'):
            company.action_archive()

        # The company can be archived because it has no active users
        user.action_archive()
        company.action_archive()

        # The user cannot be unarchived because it's default company is archived
        with self.assertRaisesRegex(ValidationError, 'Company foo is not in the allowed companies'):
            user.action_unarchive()

        # The user can be unarchived once we set another, active, company
        main_company = self.env.ref('base.main_company')
        user.write({
            'company_id': main_company.id,
            'company_ids': main_company.ids,
        })
        user.action_unarchive()

    def test_logo_check(self):
        """Ensure uses_default_logo is properly (re-)computed."""
        company = self.env['res.company'].create({'name': 'foo'})

        self.assertTrue(company.logo, 'Should have a default logo')
        self.assertTrue(company.uses_default_logo)
        company.partner_id.image_1920 = False
        # No logo means we fall back to another default logo for the website route -> uses_default
        self.assertTrue(company.uses_default_logo)
        company.partner_id.image_1920 = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
        self.assertFalse(company.uses_default_logo)

    def _create_companies(self):
        return self.env['res.company'].create([{'name': f'company_{i}'} for i in range(4)])

    def test_setting_parent_company_for_single_child(self):
        child_1, _, parent_1, parent_2 = self._create_companies()

        # Can set parent company only for the first time
        child_1.write({'parent_id': parent_1.id})

        # The company hierarchy cannot be changed.
        with self.assertRaises(UserError):
            child_1.write({'parent_id': parent_2.id})

    def test_setting_parent_company_for_multiple_children_01(self):
        companies = self._create_companies()
        children, parent_1, parent_2 = companies[:2], companies[2], companies[3]

        # Can set parent company only for the first time
        children.write({'parent_id': parent_1.id})

        # The company hierarchy cannot be changed.
        with self.assertRaises(UserError):
            children.write({'parent_id': parent_2.id})
