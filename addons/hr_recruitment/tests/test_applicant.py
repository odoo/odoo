from odoo.tests.common import TransactionCase
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
