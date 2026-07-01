import ast

from odoo.tests import tagged, TransactionCase


@tagged('recruitment_allowed_recruiters')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestRecruitmentAllowedRecruiters(TransactionCase):

    def setUp(self):
        super().setUp()

        self.env = self.env(context=dict(self.env.context, tracking_disable=True))

        self.company_a = self.env['res.company'].create({'name': 'Company A'})
        self.company_b = self.env['res.company'].create({'name': 'Company BBS'})

        # Internal user + employee in company A
        self.user_a = self.env['res.users'].create({
            'name': 'User A',
            'login': 'usera@test.com',
            'email': 'usera@test.com',
            'share': False,
            'company_ids': [self.company_a.id],
            'company_id': self.company_a.id,
            'group_ids': [self.env.ref('hr_recruitment.group_hr_recruitment_user').id]
        })
        self.employee_a = self.env['hr.employee'].create({
            'name': self.user_a.name,
            'user_id': self.user_a.id,
            'company_id': self.company_a.id,
        })

        # Internal user + employee in company B
        self.user_b = self.env['res.users'].create({
            'name': 'User B',
            'login': 'userb@test.com',
            'email': 'userb@test.com',
            'share': False,
            'company_ids': [self.company_b.id],
            'company_id': self.company_b.id,
            'group_ids': [self.env.ref('hr_recruitment.group_hr_recruitment_user').id]
        })
        self.employee_b = self.env['hr.employee'].create({
            'name': self.user_b.name,
            'user_id': self.user_b.id,
            'company_id': self.company_b.id,
        })

        # Users with different access rights and their employees
        self.dep_a = self.env['hr.department'].create({
                'name': 'Research & Development at Company A',
                'company_id': self.company_a.id,
            })

        # 1. Manager at Company B
        self.manager_user_company_b = self.env['res.users'].create({
            'name': 'Mannie the Manager',
            'login': 'mannie',
            'email': 'mannie@companyB.com',
            'company_ids': [self.company_b.id],
            'company_id': self.company_b.id,
            'group_ids': [self.env.ref('hr_recruitment.group_hr_recruitment_manager').id]
        })
        self.manager_employee_company_b = self.env['hr.employee'].create({
                    'name': self.manager_user_company_b.name,
                    'user_id': self.manager_user_company_b.id,
                    'company_id': self.company_b.id,
                })

        # 2. Recruitment Officer at Company A
        self.officer_user_company_a = self.env['res.users'].create({
            'name': 'Oliver the Officer',
            'login': 'oliver',
            'email': 'oliver@company.com',
            'company_ids': [self.company_a.id],
            'company_id': self.company_a.id,
            'group_ids': [self.env.ref('hr_recruitment.group_hr_recruitment_user').id]
        })
        self.officer_employee_company_a = self.env['hr.employee'].create({
                    'name': self.officer_user_company_a.name,
                    'user_id': self.officer_user_company_a.id,
                    'company_id': self.company_a.id,
                })

        # 3. Interviewer at Company A
        self.interviewer_user_company_a = self.env['res.users'].create({
            'name': 'Ian the Interviewer',
            'login': 'ian',
            'email': 'ian@company.com',
            'company_ids': [self.company_a.id],
            'company_id': self.company_a.id,
            'group_ids': [self.env.ref('hr_recruitment.group_hr_recruitment_interviewer').id]
        })

        self.interviewer_employee_company_a = self.env['hr.employee'].create({
            'name': self.interviewer_user_company_a.name,
            'user_id': self.interviewer_user_company_a.id,
            'company_id': self.company_a.id,
        })

    def _get_allowed_recruiters(self, record):
        # The recruiter field carries a client-side string domain referencing
        # `company_id`; bind that single variable, then parse it with
        # ast.literal_eval (CI forbids safe_eval).
        domain_str = record.fields_get(['recruiter_id'])['recruiter_id']['domain']
        domain = ast.literal_eval(domain_str.replace(', company_id)', f', {record.company_id.id})'))
        return self.env['hr.employee'].search(domain)

    def test_recruiter_with_company(self):
        # Test job with company A - should allow employee_a but not employee_b
        job_a = self.env['hr.job'].create({
            'name': 'Job Position Company A',
            'company_id': self.company_a.id,
        })

        # employee_a can be set as a recruiter
        job_a.recruiter_id = self.employee_a
        self.assertEqual(job_a.recruiter_id, self.employee_a)

        # Validate that the domain defined on hr.job.recruiter_id contains employee_a, but excludes employee_b
        allowed_recruiter_ids = self._get_allowed_recruiters(job_a)
        self.assertIn(self.employee_a, allowed_recruiter_ids)
        self.assertNotIn(self.employee_b, allowed_recruiter_ids)

    def test_recruiter_without_company(self):
        """A job position visible to all companies offers recruiters from every company."""
        job = self.env['hr.job'].create({
            'name': 'Job Position Without Company',
            'company_id': False,
        })

        allowed_recruiter_ids = self._get_allowed_recruiters(job)
        self.assertIn(self.employee_a, allowed_recruiter_ids)
        self.assertIn(self.employee_b, allowed_recruiter_ids)

    def test_applicant_access_rights(self):
        job = self.env['hr.job'].create({
            'name': "Job Position at Company A",
            'company_id': self.company_a.id,
        })

        applicant = self.env['hr.applicant'].create({
            'partner_name': "Tito Applicantson",
            'job_id': job.id,
            'company_id': self.company_a.id,
            'department_id': self.dep_a.id,
        })

        allowed_recruiter_ids = self._get_allowed_recruiters(applicant)

        self.assertNotIn(self.manager_employee_company_b, allowed_recruiter_ids, "Manager of different company should not appear in recruiter dropdown.")
        self.assertIn(self.officer_employee_company_a, allowed_recruiter_ids, "Officer should appear in recruiter dropdown.")
        self.assertNotIn(self.interviewer_employee_company_a, allowed_recruiter_ids, "Access error: Interviewer should not appear in recruiter dropdown.")

    def test_applicant_recruiter_without_company(self):
        """An applicant without a company offers recruiters from every company."""
        job = self.env['hr.job'].create({
            'name': 'Job Position Without Company',
            'company_id': False,
        })
        applicant = self.env['hr.applicant'].create({
            'partner_name': "Tito Applicantson",
            'job_id': job.id,
            'company_id': False,
        })

        allowed_recruiter_ids = self._get_allowed_recruiters(applicant)
        self.assertIn(self.manager_employee_company_b, allowed_recruiter_ids)
        self.assertIn(self.officer_employee_company_a, allowed_recruiter_ids)
