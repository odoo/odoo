from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.tests import tagged, users


@tagged('-at_install', 'post_install')
class TestCrmProjectMultiCompany(TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._activate_multi_company()
        cls.user_sales_manager_mc.group_ids += cls.env.ref('project.group_project_manager')
        cls.project_template = cls.env['project.project'].with_context(no_create_folder=True).create({
            'name': 'Test Project Template',
            'is_template': True,
            'allow_billable': True,
            'company_id': cls.company_main.id,
        })

    @users('user_sales_manager_mc')
    def test_create_project_from_lead_template(self):
        lead = self.env['crm.lead'].create({
            'name': 'Test Lead',
            'partner_name': 'Test Partner Company',
            'team_id': self.team_company2.id,
        })

        ctx = lead._get_project_create_from_lead_context()
        wizard = self.env['project.template.create.wizard'].with_context(**ctx).create({
            'name': 'New Project from Lead',
            'template_id': self.project_template.id,
        })
        wizard.action_create_project_from_lead()
        project = lead.project_ids
        self.assertEqual(project.company_id, lead.company_id)
