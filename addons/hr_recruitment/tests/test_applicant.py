from odoo.tests.common import TransactionCase, new_test_user
from odoo.tests import tagged


@tagged('hr_applicant')
class TestHrApplicant(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Category = self.env['hr.applicant.category']
        self.Candidate = self.env['hr.candidate']
        self.Applicant = self.env['hr.applicant']

        self.category_1 = self.Category.create({'name': 'Category 1'})
        self.category_2 = self.Category.create({'name': 'Category 2'})
        self.category_3 = self.Category.create({'name': 'Category 3'})

        self.candidate_0 = self.Candidate.create({
            'partner_name': 'Candidate without tag',
            'categ_ids': False
        })
        self.candidate_1 = self.Candidate.create({
            'partner_name': 'Candidate with first and second tags',
            'categ_ids': [self.category_1.id, self.category_2.id]
        })
        self.candidate_2 = self.Candidate.create({
            'partner_name': 'Candidate with second tag',
            'categ_ids': [self.category_2.id]
        })
        self.candidate_3 = self.Candidate.create({
            'partner_name': 'Candidate with third tag',
            'categ_ids': [self.category_3.id]
        })

        self.applicant = self.Applicant.create({
            'partner_name': 'Applicant',
            'candidate_id': self.candidate_0.id,
            'categ_ids': False
        })

    def test_compute_categ_ids(self):
        """
            Test that applicant.categ_ids is set correctly based on candidate_id.
        """
        # Applicant tags: None
        self.assertFalse(self.applicant.categ_ids)
        self.applicant.candidate_id = self.candidate_1.id
        # Applicant tags: 1, 2
        self.assertCountEqual(self.applicant.categ_ids.ids, [self.category_1.id, self.category_2.id])
        self.applicant.candidate_id = self.candidate_2.id
        # Applicant tags: 1, 2
        self.assertCountEqual(self.applicant.categ_ids.ids, [self.category_1.id, self.category_2.id])
        self.applicant.candidate_id = self.candidate_3.id
        # Applicant tags: 1, 2, 3
        self.assertCountEqual(self.applicant.categ_ids.ids, [self.category_1.id, self.category_2.id, self.category_3.id])
        self.applicant.candidate_id = self.candidate_0.id
        # Applicant tags: 1, 2, 3
        self.assertCountEqual(self.applicant.categ_ids.ids, [self.category_1.id, self.category_2.id, self.category_3.id])

    def test_update_interviewer_for_multiple_applicants(self):
        """
            Test that assigning interviewer to multiple applicants.
        """
        interviewer_user_1 = new_test_user(self.env, 'sma',
            groups='base.group_user,hr_recruitment.group_hr_recruitment_interviewer',
            name='Recruitment Interviewer', email='sma@example.com')

        interviewer_user_2 = new_test_user(self.env, 'jab',
            groups='base.group_user,hr_recruitment.group_hr_recruitment_interviewer',
            name='Recruitment Interviewer', email='jab@example.com')

        interviewer_user_3 = new_test_user(self.env, 'aad',
            groups='base.group_user,hr_recruitment.group_hr_recruitment_interviewer',
            name='Recruitment Interviewer', email='aad@example.com')

        applicant = self.applicant
        applicant.write({'interviewer_ids': [(6, 0, [interviewer_user_1.id])]})
        applicants = applicant + applicant.copy({'interviewer_ids': [(6, 0, [interviewer_user_2.id])]})
        # update interviewer to multiple applicants.
        applicants.write({'interviewer_ids': [(4, interviewer_user_3.id)]})

        # Ensure all interviewers are assigned
        self.assertCountEqual(
            applicants.interviewer_ids.ids, [interviewer_user_1.id, interviewer_user_2.id, interviewer_user_3.id]
        )

        # Checked that notification message is created
        message = self.env['mail.message'].search([('res_id', '=', applicant.id)], limit=1)
        self.assertEqual(message.subject, f"You have been assigned as an interviewer for {applicant.display_name}")
