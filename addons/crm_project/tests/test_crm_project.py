from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.crm.tests.common import TestCrmCommon


@tagged('at_install', '-post_install')
class TestCrmProject(TestCrmCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += (
            cls.env.ref('project.group_project_user')
            + cls.env.ref('project.group_project_manager')
        )
        cls.template = cls.env['project.project'].create({
            'name': 'Service Template',
            'is_template': True,
            'task_ids': [Command.create({'name': 'Kickoff meeting'})],
        })

    def _create_project_from_lead(self, lead, **wizard_values):
        """Go through the wizard the same way the 'Create Project' action does."""
        action = lead.action_create_project()
        wizard = self.env['project.template.create.wizard'].with_context(action['context']).create(wizard_values)
        wizard.action_create_project_from_lead()
        return lead.project_ids

    def test_create_project_from_lead(self):
        """The project created from a lead is linked to it and named after it."""
        project = self._create_project_from_lead(self.lead_1, customer_action='nothing')
        self.assertEqual(len(project), 1)
        self.assertEqual(project.name, self.lead_1.name)
        self.assertEqual(project.lead_id, self.lead_1)
        self.assertEqual(self.lead_1.project_count, 1)
        self.assertFalse(project.partner_id, "No customer should be set on the project")
        self.assertFalse(self.lead_1.partner_id, "The lead should be left without customer")
        self.assertTrue(project.is_opportunity_button_visible)

    def test_opportunity_button_hidden_without_lead(self):
        project = self.env['project.project'].create({'name': 'Standalone Project'})
        self.assertFalse(project.is_opportunity_button_visible)

    def test_create_project_from_lead_creating_customer(self):
        """A customer is created from the lead and set on both the lead and the project."""
        self.assertFalse(self.lead_1.partner_id)
        project = self._create_project_from_lead(self.lead_1, customer_action='create')
        self.assertTrue(self.lead_1.partner_id, "A customer should have been created for the lead")
        self.assertEqual(self.lead_1.partner_id.name, 'Amy Wong')
        self.assertEqual(project.partner_id, self.lead_1.partner_id)

    def test_create_project_from_lead_with_existing_customer(self):
        """An existing customer is set on both the lead and the project."""
        partner = self.env['res.partner'].create({'name': 'Planet Express'})
        project = self._create_project_from_lead(
            self.lead_1, customer_action='exist', partner_id=partner.id,
        )
        self.assertEqual(self.lead_1.partner_id, partner)
        self.assertEqual(project.partner_id, partner)

    def test_create_project_from_lead_with_template(self):
        """The project is created from the template, keeping the link to the lead."""
        project = self._create_project_from_lead(
            self.lead_1,
            name='Spacecraft Delivery',
            template_id=self.template.id,
            customer_action='create',
        )
        self.assertEqual(project.name, 'Spacecraft Delivery')
        self.assertFalse(project.is_template, "The created project is not a template itself")
        self.assertEqual(project.lead_id, self.lead_1)
        self.assertEqual(project.partner_id, self.lead_1.partner_id,
            "The customer is set from the wizard, as it is never copied from the template")
        self.assertEqual(project.task_ids.mapped('name'), ['Kickoff meeting'])
        self.assertEqual(self.lead_1.task_count, 1)

    def test_action_view_project_ids(self):
        """The stat button opens the tasks of the project, or the list of projects."""
        self._create_project_from_lead(self.lead_1, customer_action='nothing')
        action = self.lead_1.action_view_project_ids()
        self.assertEqual(action['res_model'], 'project.task')
        self.assertEqual(action['context']['default_lead_id'], self.lead_1.id)

        self._create_project_from_lead(self.lead_1, customer_action='nothing')
        self.assertEqual(self.lead_1.project_count, 2)
        action = self.lead_1.action_view_project_ids()
        self.assertEqual(action['res_model'], 'project.project')
        self.assertEqual(
            self.env['project.project'].search(action['domain']),
            self.lead_1.project_ids,
        )

    def test_action_view_lead(self):
        """The project gives access back to the lead it was created from."""
        project = self._create_project_from_lead(self.lead_1, customer_action='nothing')
        action = project.action_view_lead()
        self.assertEqual(action['res_model'], 'crm.lead')
        self.assertEqual(action['res_id'], self.lead_1.id)
