from odoo.addons.base.tests.common import BaseCommon


class AnalyticCommon(BaseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.analytic_plan_offset = len(cls.env['account.analytic.plan'].sudo().get_relevant_plans())
        cls.analytic_plan_1, cls.analytic_plan_2 = cls.env['account.analytic.plan'].sudo().create([
            {
                'name': 'Plan 1',
                'default_applicability': 'unavailable',
            },
            {
                'name': 'Plan 2',
            }
        ])
        cls.analytic_plan_child = cls.env['account.analytic.plan'].sudo().create({
            'name': 'Plan Child',
            'parent_id': cls.analytic_plan_1.id,
        })

        cls.analytic_account_1, cls.analytic_account_2, cls.analytic_account_3, cls.analytic_account_4 = cls.env['account.analytic.account'].sudo().create([
            {'name': 'Account 1', 'plan_id': cls.analytic_plan_1.id, 'company_id': False},
            {'name': 'Account 2', 'plan_id': cls.analytic_plan_child.id, 'company_id': False},
            {'name': 'Account 3', 'plan_id': cls.analytic_plan_2.id, 'company_id': False},
            {'name': 'Account 4', 'plan_id': cls.analytic_plan_2.id, 'company_id': False}
        ])

    @classmethod
    def setup_independent_company(cls, **kwargs):
        # OVERRIDE
        company = super().setup_independent_company(**kwargs)
        if not company:
            company = cls._create_company(name='analytic', **kwargs)
        return company

    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        return groups + cls.env.ref('analytic.group_analytic_accounting')

    @classmethod
    def _enable_analytic_accounting(cls):
        cls.user.groups_id += cls.env.ref('analytic.group_analytic_accounting')
