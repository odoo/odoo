from .test_multicompany import TestMultiCompanyProject

from odoo.exceptions import UserError


class TestProjectStagesMulticompany(TestMultiCompanyProject):

    @classmethod
    def setUpClass(cls):
        super(TestProjectStagesMulticompany, cls).setUpClass()

        Users = cls.env['res.users'].with_context({'no_reset_password': True})
        cls.user_manager_companies = Users.create({
            'name': 'Manager Companies',
            'login': 'manager-all',
            'email': 'manager@companies.com',
            'company_id': cls.company_a.id,
            'company_ids': [(4, cls.company_a.id), (4, cls.company_b.id)],
            'groups_id':
                [(6, 0, [
                    cls.env.ref('base.group_user').id,
                    cls.env.ref('project.group_project_stages').id,
                    cls.env.ref('project.group_project_manager').id,
                ])]
        })
        cls.stage_company_a, cls.stage_company_b, cls.stage_company_none = cls.env['project.project.stage'].create([{
            'name': 'Stage Company A',
            'company_id': cls.company_a.id,
        }, {
            'name': 'Stage Company B',
            'company_id': cls.company_b.id,
        }, {
            'name': 'Stage Company None',
        }])
        cls.project_company_none = cls.env['project.project'].create({
            'name': 'Project Company None'
        })

    def test_move_linked_project_stage_other_company(self):
        """ This test will check that an error is raised if a project belonging to a stage
        (both linked to company A) is moved to another stage (belonging to company B) """
        self.project_company_a.stage_id = self.stage_company_a.id
        with self.assertRaises(UserError):
            self.project_company_a.stage_id = self.stage_company_b.id

    def test_move_project_stage_other_company(self):
        """ This test will check that an error is raised a project belonging to a stage (both
        not linked to any company) is moved to another stage (belonging to company B) """
        self.project_company_none.stage_id = self.stage_company_none.id
        with self.assertRaises(UserError):
            self.project_company_none.stage_id = self.stage_company_b.id,

    def test_move_linked_project_stage_same_company(self):
        """ This test will check that no error is raised if a project belonging to a stage (with
        only the project belonging to company B and the stage not linked to any company) is moved
        to another stage (belonging to company B) """
        self.project_company_b.stage_id = self.stage_company_none.id
        self.project_company_b.stage_id = self.stage_company_b.id

    def test_move_project_stage_same_company(self):
        """ This test will check that no error is raised if a project belonging to a stage (both
        linked to company A) is moved to another stage (also belonging to company A) """
        self.project_company_a.stage_id = self.stage_company_a.id
        self.stage_company_none.company_id = self.company_a.id
        self.project_company_a.stage_id = self.stage_company_none.id

    def test_change_project_company(self):
        """ This test will check that a project's stage is changed according to the
        company it is linked to. When a project (belonging to a stage with both the
        project and the stage linked to company A) changes company for company B,
        the stage should change for the lowest stage in sequence that is linked to
        company B. If there is no stage linked to company B, then the lowest stage
        in sequence linked to no company will be chosen """
        project = self.project_company_a.with_user(self.user_manager_companies)
        project.stage_id = self.stage_company_a.id
        project.company_id = self.company_b.id

        # Check that project was moved to stage_company_b
        self.assertFalse(self.project_company_a.stage_id.company_id, "Project Company A should now be in a stage without company")

    def test_project_creation_default_stage(self):
        """
         Check that when creating a project with a company set, the default stage
         for this project has the same company as the project or no company.
         If no company is set on the project, the first stage without a company
         should be chosen.
        """
        # Stage order: company A, company B, no company
        self.stage_company_a.sequence = 1
        self.stage_company_b.sequence = 3

        project_company_b = self.env['project.project'].with_user(self.user_manager_companies).create({
            'name': 'Project company B',
            'company_id': self.company_b.id,
        })
        self.assertEqual(project_company_b.company_id, self.company_b)
        self.assertEqual(project_company_b.stage_id, self.stage_company_b)

        # Stage order: company A, no company, company B
        self.stage_company_none.sequence = 2

        project_company_b = self.env['project.project'].with_user(self.user_manager_companies).create({
            'name': 'Project company B',
            'company_id': self.company_b.id,
        })
        self.assertEqual(project_company_b.company_id, self.company_b)
        self.assertEqual(project_company_b.stage_id, self.stage_company_none)

        project_no_company = self.env['project.project'].with_user(self.user_manager_companies).create({
            'name': 'Project no company',
        })
        self.assertFalse(project_no_company.company_id)
        self.assertEqual(project_no_company.stage_id, self.stage_company_none)

        self.env['project.project.stage'].search([]).active = False
        project_no_company = self.env['project.project'].with_user(self.user_manager_companies).create({
            'name': 'Project no company',
        })
        self.assertFalse(project_no_company.stage_id)

    def test_project_creation_default_stage_in_context(self):
        """
        Project's company should be the same as the default stage's company in the context.
        """
        project = self.env['project.project'].with_user(self.user_manager_companies).with_context(default_stage_id=self.stage_company_b.id).create({
            'name': 'Project company B',
        })
        self.assertEqual(project.company_id, self.company_b)
