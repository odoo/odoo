from odoo.addons.base.tests.common import BaseCommon
from odoo.tests.common import new_test_user


class AnalyticCommon(BaseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.analytic_plan_offset = len(cls.env['account.analytic.plan'].get_relevant_plans())
        cls.analytic_plan_1, cls.analytic_plan_2 = cls.env['account.analytic.plan'].create([
            {
                'name': 'Plan 1',
                'default_applicability': 'unavailable',
            },
            {
                'name': 'Plan 2',
            }
        ])
        cls.analytic_plan_child = cls.env['account.analytic.plan'].create({
            'name': 'Plan Child',
            'parent_id': cls.analytic_plan_1.id,
        })

        cls.analytic_account_1, cls.analytic_account_2, cls.analytic_account_3, cls.analytic_account_4 = cls.env['account.analytic.account'].create([
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
    def setup_independent_user(cls):
        # Add group_system to be able to create companies notably in the class setup
        default_groups = cls.env.ref('base.group_system') + cls.get_default_groups()
        # Removes access rights linked to timesheet and project as these add
        # record rules blocking analytic flows; account overrides it
        if 'account.account' not in cls.env:
            core_group_ids = cls.env.ref("hr_timesheet.group_hr_timesheet_user", raise_if_not_found=False) or cls.env['res.groups']
            problematic_group_ids = default_groups.filtered(lambda g: (g | g.trans_implied_ids) & core_group_ids)
            if problematic_group_ids:
                default_groups -= problematic_group_ids
        return new_test_user(
            cls.env,
            name='The anal(ytic) expert!',
            login='analytic',
            password='analytic',
            email='analyticman@test.com',
            groups_id=default_groups.ids,
            company_id=cls.env.company.id,
        )
