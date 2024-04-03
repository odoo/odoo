# -*- coding: utf-8 -*-

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo import Command
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAnalyticAccount(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.analytic_plan_1 = cls.env['account.analytic.plan'].create({
            'name': 'Plan 1',
            'default_applicability': 'unavailable',
            'company_id': False,
        })
        cls.analytic_plan_child = cls.env['account.analytic.plan'].create({
            'name': 'Plan Child',
            'parent_id': cls.analytic_plan_1.id,
            'company_id': False,
        })
        cls.analytic_plan_2 = cls.env['account.analytic.plan'].create({
            'name': 'Plan 2',
            'company_id': False,
        })

        # Create new user to avoid demo data.
        user = cls.env['res.users'].create({
            'name': 'The anal(ytic) expert!',
            'login': 'analytic',
            'password': 'analytic',
            'groups_id': [
                (6, 0, cls.env.user.groups_id.ids),
                (4, cls.env.ref('analytic.group_analytic_accounting').id),
            ],
        })
        user.partner_id.email = 'analyticman@test.com'

        # Shadow the current environment/cursor with one having the report user.
        # This is mandatory to test access rights.
        cls.env = cls.env(user=user)
        cls.cr = cls.env.cr

        cls.company_data = cls.env['res.company'].create({
            'name': 'company_data',
        })
        cls.env.user.company_ids |= cls.company_data

        user.write({
            'company_ids': [(6, 0, cls.company_data.ids)],
            'company_id': cls.company_data.id,
        })

        cls.partner_a = cls.env['res.partner'].create({'name': 'partner_a', 'company_id': False})
        cls.partner_b = cls.env['res.partner'].create({'name': 'partner_b', 'company_id': False})

        cls.analytic_account_1 = cls.env['account.analytic.account'].create({'name': 'Account 1', 'plan_id': cls.analytic_plan_1.id})
        cls.analytic_account_2 = cls.env['account.analytic.account'].create({'name': 'Account 2', 'plan_id': cls.analytic_plan_child.id})
        cls.analytic_account_3 = cls.env['account.analytic.account'].create({'name': 'Account 3', 'plan_id': cls.analytic_plan_2.id})

        cls.distribution_1 = cls.env['account.analytic.distribution.model'].create({
            'partner_id': cls.partner_a.id,
            'analytic_distribution': {cls.analytic_account_3.id: 100}
        })

        cls.distribution_2 = cls.env['account.analytic.distribution.model'].create({
            'partner_id': cls.partner_b.id,
            'analytic_distribution': {cls.analytic_account_2.id: 100}
        })

    def test_get_plans_without_options(self):
        """ Test that the plans with the good appliability are returned without if no options are given """
        kwargs = {}
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(1, len(plans_json), "Only the Default plan should be available")

        self.analytic_plan_1.write({'default_applicability': 'mandatory'})
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(2, len(plans_json), "All root plans should be available")

    def test_get_plans_with_option(self):
        """ Test the plans returned with applicability rules and options """
        kwargs = {'business_domain': 'general'}
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(1, len(plans_json), "Only the Default plan should be available")

        applicability = self.env['account.analytic.applicability'].create({
            'business_domain': 'general',
            'analytic_plan_id': self.analytic_plan_1.id,
            'applicability': 'mandatory'
        })
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(2, len(plans_json), "All root plans should be available")

        self.analytic_plan_1.write({'default_applicability': 'mandatory'})
        applicability.write({'applicability': 'unavailable'})
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(1, len(plans_json), "Plan 1 should be unavailable")

        kwargs = {'business_domain': 'purchase_order'}
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(2, len(plans_json), "Both plans should be available")

        kwargs = {'applicability': 'optional'}
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(2, len(plans_json), "All root plans should be available")

    def test_analytic_distribution_model(self):
        """ Test the distribution returned from the distribution model """
        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({})
        self.assertEqual(distribution_json, {}, "No distribution should be given")
        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_a.id,
            "company_id": self.company_data.id,
        })
        self.assertEqual(distribution_json, {str(self.analytic_account_3.id): 100}, "Distribution 1 should be given")
        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_b.id,
            "company_id": self.company_data.id,
        })
        self.assertEqual(distribution_json, {str(self.analytic_account_2.id): 100}, "Distribution 2 should be given")

    def test_order_analytic_distribution_model(self):
        """ Test the distribution returned with company field"""
        distribution_3 = self.env['account.analytic.distribution.model'].create({
            'partner_id': self.partner_a.id,
            'analytic_distribution': {self.analytic_account_1.id: 100},
            'company_id': self.company_data.id,
        })
        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({})
        self.assertEqual(distribution_json, {}, "No distribution should be given")

        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_a.id,
            "company_id": self.company_data.id,
        })
        self.assertEqual(distribution_json, distribution_3.analytic_distribution,
                         "Distribution 3 should be given, as the company is specified in the model")

        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_b.id,
            "company_id": self.company_data.id,
        })
        self.assertEqual(distribution_json, {str(self.analytic_account_2.id): 100},
                         "Distribution 2 should be given, for the partner")

        partner_category = self.env['res.partner.category'].create({'name': 'partner_categ'})
        self.partner_a.write({
            'category_id': [Command.set([partner_category.id])]
        })

        distribution_4 = self.env['account.analytic.distribution.model'].create({
            'partner_id': self.partner_a.id,
            'analytic_distribution': {self.analytic_account_1.id: 100, self.analytic_account_2.id: 100},
            'partner_category_id': partner_category.id,
        })

        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_a.id,
            "company_id": self.company_data.id,
            "partner_category_id": partner_category.ids,
        })
        self.assertEqual(distribution_json, distribution_4.analytic_distribution,
                         "Distribution 4 should be given, as the partner_category_id is better than the company_id")

    def test_analytic_plan_account_child(self):
        """
        Check that when an analytic account is set to the third (or more) child,
        the root plan is correctly retrieved.
        """
        self.analytic_plan = self.env['account.analytic.plan'].create({
            'name': 'Parent Plan',
            'company_id': False,
        })
        self.analytic_sub_plan = self.env['account.analytic.plan'].create({
            'name': 'Sub Plan',
            'parent_id': self.analytic_plan.id,
            'company_id': False,
        })
        self.analytic_sub_sub_plan = self.env['account.analytic.plan'].create({
            'name': 'Sub Sub Plan',
            'parent_id': self.analytic_sub_plan.id,
            'company_id': False,
        })
        self.analytic_account_1 = self.env['account.analytic.account'].create({'name': 'Child Account', 'plan_id': self.analytic_sub_sub_plan.id})
        plans_json = self.env['account.analytic.plan'].get_relevant_plans()
        self.assertEqual(2, len(plans_json),
                         "The parent plan should be available even if the analytic account is set on child of third generation")

    def test_analytic_plan_account_parent(self):
        """
        Check that when assigning an analytic plan as the parent to a child analytic plan,
        both plans must belong to the same company.
        """
        company_1, company_2 = self.env['res.company'].create([
            {'name': 'company_1'},
            {'name': 'company_2'}
        ])
        self.env.user.company_ids |= company_1 + company_2
        parent_analytic_plan_1, parent_analytic_plan_2 = self.env['account.analytic.plan'].create([{
            'name': 'Parent Plan 1',
            'company_id': company_1.id,
        }, {
            'name': 'Parent Plan 2',
            'company_id': company_1.id,
        }])
        child_analytic_plan_1 = self.env['account.analytic.plan'].create({
            'name': 'Child Plan 1',
            'company_id': company_1.id,
            'parent_id': parent_analytic_plan_1.id,
        })
        self.assertEqual(child_analytic_plan_1.parent_id.id, parent_analytic_plan_1.id)
        with self.assertRaises(UserError):
            self.env['account.analytic.plan'].create({
                'name': 'Chils Plan 2',
                'company_id': company_2.id,
                'parent_id': parent_analytic_plan_2.id,
            })
