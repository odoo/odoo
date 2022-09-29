# -*- coding: utf-8 -*-

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


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

        kwargs = {'business_domain': 'purchase'}
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
        })
        self.assertEqual(distribution_json, {str(self.analytic_account_3.id): 100}, "Distribution 1 should be given")
        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_b.id,
        })
        self.assertEqual(distribution_json, {str(self.analytic_account_2.id): 100}, "Distribution 2 should be given")
