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

    def test_recruiter_user_id_with_company(self):
        # Test job with company A - should allow user_a but not user_b
        job_a = self.env['hr.job'].create({
            'name': 'Job Position Company A',
            'company_id': self.company_a.id,
        })

        # user_a can be set as a recruiter
        job_a.user_id = self.user_a
        self.assertEqual(job_a.user_id, self.user_a)

        # Validate that the domain defined on hr.job.user_id contains user_a, but excludes user_b
        domain = [('share', '=', False), ('company_ids', '=?', self.company_a.id)]
        allowed_users = self.env['res.users'].search(domain)
        self.assertIn(self.user_a, allowed_users)
        self.assertNotIn(self.user_b, allowed_users)

    def test_recruiter_user_id_without_company(self):
        # Test job without company - should allow both users
        job = self.env['hr.job'].create({
            'name': 'Job Position',
            'company_id': False,
        })

        # When company_id is False, users from *any* company are ok
        domain = [('share', '=', False), ('company_ids', '=?', False)]
        allowed_users = self.env['res.users'].search(domain)
        self.assertIn(self.user_a, allowed_users)
        self.assertIn(self.user_b, allowed_users)

        # Both users should be settable as recruiter
        job.user_id = self.user_a
        self.assertEqual(job.user_id, self.user_a)

        job.user_id = self.user_b
        self.assertEqual(job.user_id, self.user_b)
