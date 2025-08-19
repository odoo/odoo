# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
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

    def test_create_branch_with_default_parent_id(self):
        branch = self.env['res.company'].with_context(default_parent_id=self.env.company.id).create({'name': 'Branch Company'})
        self.assertFalse(branch.partner_id.parent_id)

    def test_update_partner_company_id(self):
        # Create a company (parent) partner
        parent_company_partner = self.env['res.partner'].create({'name': 'Test Partner 1'})
        # Create a company object linked to the parent partner
        parent_company = self.env['res.company'].create({
            'name': 'Test Company',
            'partner_id': parent_company_partner.id,
        })

        # Link the partner to the company
        parent_company_partner.company_id = parent_company.id

        # Create a child contact with a parent (inherits company)
        child_partner = self.env['res.partner'].create({
            'name': 'Child Contact',
            'company_id': parent_company.id,
            'parent_id': parent_company_partner.id,
        })

        # Try to update the child's company_id to something else
        another_company = self.env['res.company'].create({
            'name': 'Another Company',
        })

        with self.assertRaises(ValidationError):
            child_partner.write({
                'company_id': another_company.id,
            })
