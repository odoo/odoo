# -*- coding: utf-8 -*-

from odoo.tests import Form, tagged
from odoo import Command

from odoo.addons.analytic.tests.common import AnalyticCommon


@tagged('post_install', '-at_install')
class TestAnalyticAccount(AnalyticCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_a = cls.env['res.partner'].create({'name': 'partner_a', 'company_id': False})
        cls.partner_b = cls.env['res.partner'].create({'name': 'partner_b', 'company_id': False})

        cls.distribution_1, cls.distribution_2 = cls.env['account.analytic.distribution.model'].create([
            {
                'partner_id': cls.partner_a.id,
                'analytic_distribution': {cls.analytic_account_3.id: 100}
            },
            {
                'partner_id': cls.partner_b.id,
                'analytic_distribution': {cls.analytic_account_2.id: 100}
            },
        ])

    def test_aggregates(self):
        # debit and credit are hidden by the group when account is installed
        fields_to_agg = ['balance', 'debit', 'credit'] if self.env.user.has_group('account.group_account_readonly') else ['balance']
        model = self.env['account.analytic.account']
        self.assertEqual(
            model.fields_get(fields_to_agg, ['aggregator']),
            dict.fromkeys(fields_to_agg, {'aggregator': 'sum'}),
            f"Fields {', '.join(f for f in fields_to_agg)} must be flagged as aggregatable.",
        )

    def test_get_plans_without_options(self):
        """ Test that the plans with the good appliability are returned without if no options are given """
        kwargs = {}
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(1, len(plans_json) - self.analytic_plan_offset, "Only the Default plan and the demo data plans should be available")

        self.analytic_plan_1.write({'default_applicability': 'mandatory'})
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(2, len(plans_json) - self.analytic_plan_offset, "All root plans should be available")

    def test_get_plans_with_option(self):
        """ Test the plans returned with applicability rules and options """
        kwargs = {'business_domain': 'general'}
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(1, len(plans_json) - self.analytic_plan_offset, "Only the Default plan and the demo data plans should be available")

        applicability = self.env['account.analytic.applicability'].create({
            'business_domain': 'general',
            'analytic_plan_id': self.analytic_plan_1.id,
            'applicability': 'mandatory'
        })
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(2, len(plans_json) - self.analytic_plan_offset, "All root plans should be available")

        self.analytic_plan_1.write({'default_applicability': 'mandatory'})
        applicability.write({'applicability': 'unavailable'})
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(1, len(plans_json) - self.analytic_plan_offset, "Plan 1 should be unavailable")

        kwargs = {'business_domain': 'purchase_order'}
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(2, len(plans_json) - self.analytic_plan_offset, "Both plans should be available")

        kwargs = {'applicability': 'optional'}
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(2, len(plans_json) - self.analytic_plan_offset, "All root plans should be available")

    def test_analytic_distribution_model(self):
        """ Test the distribution returned from the distribution model """
        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({})
        self.assertEqual(distribution_json, {}, "No distribution should be given")
        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_a.id,
            "company_id": self.company.id,
        })
        self.assertEqual(distribution_json, {str(self.analytic_account_3.id): 100}, "Distribution 1 should be given")
        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_b.id,
            "company_id": self.company.id,
        })
        self.assertEqual(distribution_json, {str(self.analytic_account_2.id): 100}, "Distribution 2 should be given")

    def test_order_analytic_distribution_model(self):
        """ Test the distribution returned with company field"""
        distribution_3 = self.env['account.analytic.distribution.model'].create({
            'partner_id': self.partner_a.id,
            'analytic_distribution': {self.analytic_account_1.id: 100},
            'company_id': self.company.id,
        })
        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({})
        self.assertEqual(distribution_json, {}, "No distribution should be given")

        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_a.id,
            "company_id": self.company.id,
        })
        self.assertEqual(distribution_json, distribution_3.analytic_distribution | self.distribution_1.analytic_distribution,
                         "Distribution 3 & 1 should be given, as the company and partner are specified in the models")

        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_b.id,
            "company_id": self.company.id,
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
            'sequence': 1,
        })

        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_a.id,
            "company_id": self.company.id,
            "partner_category_id": partner_category.ids,
        })

        self.assertEqual(distribution_json, distribution_4.analytic_distribution | self.distribution_1.analytic_distribution,
                         "Distribution 4 & 1 should be given based on sequence")

    def test_analytic_plan_account_child(self):
        """
        Check that when an analytic account is set to the third (or more) child,
        the root plan is correctly retrieved.
        """
        self.analytic_plan = self.env['account.analytic.plan'].create({
            'name': 'Parent Plan',
        })
        self.analytic_sub_plan = self.env['account.analytic.plan'].create({
            'name': 'Sub Plan',
            'parent_id': self.analytic_plan.id,
        })
        self.analytic_sub_sub_plan = self.env['account.analytic.plan'].create({
            'name': 'Sub Sub Plan',
            'parent_id': self.analytic_sub_plan.id,
        })
        self.env['account.analytic.account'].create({'name': 'Account', 'plan_id': self.analytic_plan.id})
        self.env['account.analytic.account'].create({'name': 'Child Account', 'plan_id': self.analytic_sub_plan.id})
        self.env['account.analytic.account'].create({'name': 'Grand Child Account', 'plan_id': self.analytic_sub_sub_plan.id})
        plans_json = self.env['account.analytic.plan'].get_relevant_plans()
        self.assertEqual(2, len(plans_json) - self.analytic_plan_offset,
                         "The parent plan should be available even if the analytic account is set on child of third generation")

    def test_all_account_count_with_subplans(self):
        self.analytic_plan = self.env['account.analytic.plan'].create({
            'name': 'Parent Plan',
        })
        self.analytic_sub_plan = self.env['account.analytic.plan'].create({
            'name': 'Sub Plan',
            'parent_id': self.analytic_plan.id,
        })
        self.analytic_sub_sub_plan = self.env['account.analytic.plan'].create({
            'name': 'Sub Sub Plan',
            'parent_id': self.analytic_sub_plan.id,
        })

        self.env['account.analytic.account'].create([
            {'name': 'Account', 'plan_id': self.analytic_plan.id},
            {'name': 'Child Account', 'plan_id': self.analytic_sub_plan.id},
            {'name': 'Grand Child Account', 'plan_id': self.analytic_sub_sub_plan.id}
        ])

        expected_values = {self.analytic_plan: 3, self.analytic_sub_plan: 2, self.analytic_sub_sub_plan: 1}
        for plan, expected_value in expected_values.items():
            with self.subTest(plan=plan.name, expected_count=expected_value):
                with Form(plan) as plan_form:
                    self.assertEqual(plan_form.record.all_account_count, expected_value)
