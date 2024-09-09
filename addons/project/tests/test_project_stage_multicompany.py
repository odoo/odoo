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
                [(6, 0, cls.env.ref(
                    'base.group_user',
                    'project.group_project_stages',
                    'project.group_project_manager',
                    raise_if_not_found=False
                ).ids)]
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
