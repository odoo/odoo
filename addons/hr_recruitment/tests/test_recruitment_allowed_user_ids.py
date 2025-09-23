from odoo.tests import tagged, TransactionCase


@tagged('recruitment_allowed_user_ids')
class TestRecruitmentAllowedUserIds(TransactionCase):

    def setUp(self):
        super().setUp()

        self.env = self.env(context=dict(self.env.context, tracking_disable=True))

        self.company_a = self.env['res.company'].create({'name': 'Company A'})
        self.company_b = self.env['res.company'].create({'name': 'Company BBS'})

        # Internal user in company A
        self.user_a = self.env['res.users'].create({
            'name': 'User A',
            'login': 'usera@test.com',
            'email': 'usera@test.com',
            'share': False,
            'company_ids': [self.company_a.id],
            'company_id': self.company_a.id,
        })

        # Internal user in company B
        self.user_b = self.env['res.users'].create({
            'name': 'User B',
            'login': 'userb@test.com',
            'email': 'userb@test.com',
            'share': False,
            'company_ids': [self.company_b.id],
            'company_id': self.company_b.id,
        })

    def test_recruiter_allowed_user_ids_with_company(self):
        job = self.env['hr.job'].create({
            'name': 'Job Position Company A',
            'company_id': self.company_a.id,
        })
        job._compute_allowed_user_ids()

        matched_users = job.allowed_user_ids

        self.assertIn(self.user_a, matched_users)
        self.assertNotIn(self.user_b, matched_users)

        job = self.env['hr.job'].create({
            'name': 'Job Position Company B',
            'company_id': self.company_b.id,
        })
        job._compute_allowed_user_ids()

        matched_users = job.allowed_user_ids

        self.assertIn(self.user_b, matched_users)
        self.assertNotIn(self.user_a, matched_users)

    def test_recruiter_allowed_user_ids_without_company(self):
        job = self.env['hr.job'].create({
            'name': 'Job Position',
            'company_id': False,
        })
        job._compute_allowed_user_ids()

        matched_users = job.allowed_user_ids

        self.assertIn(self.user_a, matched_users)
        self.assertIn(self.user_b, matched_users)
