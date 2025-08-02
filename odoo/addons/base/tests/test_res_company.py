# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.api import lazy_property
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


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


class TestUserCompany(TransactionCase):

    def test_get_company_ids_clear_cache(self):
        self.env = self.env(user=self.env.ref('base.user_admin'))
        self.assertFalse(self.env.su)
        self.company_1 = self.env['res.company'].create({'name': 'Company 1'})
        self.company_2 = self.env['res.company'].create({'name': 'Company 2'})
        companies = self.env.user._get_company_ids()
        self.assertIn(self.company_1.id, companies)
        self.assertIn(self.company_2.id, companies)

        # ensure that cache _get_company_ids will be called during the write
        self.env.registry.clear_cache()
        self.env.invalidate_all()
        lazy_property.reset_all(self.env)
        self.company_2.with_context(allowed_company_ids=[self.company_1.id]).active = False

        companies = self.env.user._get_company_ids()
        self.assertIn(self.company_1.id, companies)
        # making this assertion fail is actually verry hard to reproduce since it will only occur if _get_company_ids is called betwwen the clear and the write
        # this is not always the case because _get_company_ids is hiden behind another lazy_property, env.companies
        # this can be warmup by some overrides, like _get_tax_closing_journal.
        self.assertNotIn(self.company_2.id, companies, "Company2 should not be in _get_company_ids after it was deactivated")

        self.env.registry.clear_cache()
        self.env.invalidate_all()
        lazy_property.reset_all(self.env)
        self.company_2.with_context(allowed_company_ids=[self.company_1.id]).active = True

        companies = self.env.user._get_company_ids()
        self.assertIn(self.company_1.id, companies)
        self.assertIn(self.company_2.id, companies, "Company2 should not be in _get_company_ids after it was deactivated")


@tagged('post_install', '-at_install')
class TestUserCompanyPostInstall(TestUserCompany):
    def test_get_company_ids_clear_cache(self):
        super().test_get_company_ids_clear_cache()
