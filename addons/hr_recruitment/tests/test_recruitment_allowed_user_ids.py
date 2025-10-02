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

    def test_applicant_access_rights(self):
        company = self.env.company

        self.manager_user = self.env['res.users'].create({
            'name': 'Mannie the Manager',
            'login': 'mannie',
            'email': 'mannie@company.com',
            'company_ids': [company.id],
            'company_id': company.id,
            'group_ids': [self.env.ref('hr_recruitment.group_hr_recruitment_manager').id]
        })
        self.manager_employee = self.env['hr.employee'].create({
                    'name': self.manager_user.name,
                    'user_id': self.manager_user.id,
                    'company_id': company.id,
                })

        self.officer_user = self.env['res.users'].create({
            'name': 'Oliver the Officer',
            'login': 'oliver',
            'email': 'oliver@company.com',
            'company_ids': [company.id],
            'company_id': company.id,
            'group_ids': [self.env.ref('hr_recruitment.group_hr_recruitment_user').id]
        })
        self.officer_employee = self.env['hr.employee'].create({
                    'name': self.officer_user.name,
                    'user_id': self.officer_user.id,
                    'company_id': company.id,
                })

        self.interviewer_user = self.env['res.users'].create({
            'name': 'Ian the Interviewer',
            'login': 'ian',
            'email': 'ian@company.com',
            'company_ids': [company.id],
            'company_id': company.id,
            'group_ids': [self.env.ref('hr_recruitment.group_hr_recruitment_interviewer').id]
        })

        self.interviewer_employee = self.env['hr.employee'].create({
            'name': self.interviewer_user.name,
            'user_id': self.interviewer_user.id,
            'company_id': company.id,
        })

        job = self.env['hr.job'].create({
            'name': "Job Position Mannie's Company",
            'company_id': company.id,
        })

        applicant = self.env['hr.applicant'].create({
            'partner_name': "Tito Applicantson",
            'job_id': job.id,
        })

        allowed_recruiter_ids = self.env['hr.employee'].search(applicant._get_hr_recruiter_domain())

        self.assertIn(self.manager_employee, allowed_recruiter_ids, "Manager should appear in recruiter dropdown")
        self.assertIn(self.officer_employee, allowed_recruiter_ids, "Officer should appear in recruiter dropdown")
        self.assertNotIn(self.interviewer_employee, allowed_recruiter_ids, "Interviewer should not appear in recruiter dropdown")
