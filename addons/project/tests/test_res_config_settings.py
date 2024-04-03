# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, Form, TransactionCase


@tagged('post_install', '-at_install')
class TestResConfigSettings(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.analytic_plan_1, cls.analytic_plan_2 = cls.env['account.analytic.plan'].create([
            {
                'name': 'Plan 1',
                'default_applicability': 'optional',
                'company_id': False,
            }, {
                'name': 'Plan 2',
                'default_applicability': 'optional',
                'company_id': False,
            },
        ])
        cls.company_1, cls.company_2 = cls.env['res.company'].create([
            {'name': 'Test Company 1'},
            {'name': 'Test Company 2'},
        ])
        (cls.analytic_plan_1 + cls.analytic_plan_2).write({
            'company_id': cls.company_1.id,
        })

    def test_set_default_analytic_plan(self):
        """
        Test that we can set the default analytic plan in the settings per company.
        When there are no analytic plans for the company, a new one named "Default" should be created.
        """
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        settings_company_1 = self.env['res.config.settings'].with_company(self.company_1).create({})
        with Form(settings_company_1) as form:
            self.assertEqual(form.analytic_plan_id, self.analytic_plan_1)
            form.analytic_plan_id = self.analytic_plan_2
            form.save()
            self.assertEqual(settings_company_1.analytic_plan_id, self.analytic_plan_2)
        settings_company_2 = self.env['res.config.settings'].with_company(self.company_2).create({})
        with Form(settings_company_2) as form:
            self.assertNotEqual(form.analytic_plan_id, self.analytic_plan_1)
            self.assertNotEqual(form.analytic_plan_id, self.analytic_plan_2)
            self.assertEqual(form.analytic_plan_id.name, "Default")
