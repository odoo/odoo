from odoo.tests import Form, tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged('-at_install', 'post_install')
class TestSaleProjectWarning(BaseCommon):
    _test_user_groups = ('project.group_project_manager',)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_warning_sale = cls.quick_ref('sale.group_warning_sale')
        cls.group_user._apply_group(cls.group_warning_sale)

        cls.partner_with_warning = cls.env['res.partner'].create({
            'name': 'Partner With Warning',
            'sale_warn_msg': 'Highly infectious disease',
        })
        # No name on purpose: the warning falls back on the display name.
        cls.child_partner_with_warning = cls.env['res.partner'].create({
            'type': 'invoice',
            'parent_id': cls.partner_with_warning.id,
            'sale_warn_msg': 'Slightly infectious disease',
        })
        cls.billable_project, cls.project_template = cls.env['project.project'].create([
            {
                'name': 'Billable Project',
                'allow_billable': True,
            },
            {
                'name': 'Billable Project Template',
                'allow_billable': True,
                'is_template': True,
            },
        ])
        cls.partner_warning = "Partner With Warning - Highly infectious disease"
        cls.child_partner_warning = (
            "Partner With Warning, Invoice - Slightly infectious disease\n"
            "Partner With Warning - Highly infectious disease"
        )

    def test_project_sale_warning_text(self):
        project = self.env['project.project'].create({
            'name': 'Project',
            'allow_billable': True,
            'partner_id': self.partner_with_warning.id,
        })
        self.assertEqual(
            project.sale_warning_text,
            self.partner_warning,
            "The project should display the sale warning of its customer.",
        )

        project.partner_id = self.child_partner_with_warning
        self.assertEqual(
            project.sale_warning_text,
            self.child_partner_warning,
            "The warning of the parent partner should be displayed after the one of its contact.",
        )

        project.partner_id = self.partner
        self.assertFalse(
            project.sale_warning_text,
            "No warning should be displayed for a customer without sale warning.",
        )

        project.partner_id = False
        self.assertFalse(
            project.sale_warning_text,
            "No warning should be displayed on a project without customer.",
        )

    def test_project_sale_warning_text_form(self):
        with Form(
            self.env['project.project'].with_context(default_allow_billable=True),
            view='project.project_project_view_form_simplified',
        ) as project_form:
            project_form.name = 'Project'
            self.assertFalse(
                project_form.sale_warning_text,
                "No warning should be displayed before a customer is set.",
            )
            project_form.partner_id = self.partner_with_warning
            self.assertEqual(
                project_form.sale_warning_text,
                self.partner_warning,
                "The warning should be displayed as soon as the customer is set in the form.",
            )
            project_form.partner_id = self.child_partner_with_warning
            self.assertEqual(
                project_form.sale_warning_text,
                self.child_partner_warning,
                "The warning should be updated when the customer changes in the form.",
            )

    def test_task_sale_warning_text(self):
        task = self.env['project.task'].create({
            'name': 'Task',
            'project_id': self.billable_project.id,
            'partner_id': self.partner_with_warning.id,
        })
        self.assertEqual(
            task.sale_warning_text,
            self.partner_warning,
            "The task should display the sale warning of its customer.",
        )

        task.partner_id = self.child_partner_with_warning
        self.assertEqual(
            task.sale_warning_text,
            self.child_partner_warning,
            "The warning of the parent partner should be displayed after the one of its contact.",
        )

        (self.partner_with_warning + self.child_partner_with_warning).sudo().sale_warn_msg = False
        self.assertFalse(
            task.sale_warning_text,
            "The warning should be removed once the message is removed from the partner.",
        )

    def test_task_sale_warning_text_form(self):
        task = self.env['project.task'].create({
            'name': 'Task',
            'project_id': self.billable_project.id,
        })
        with Form(task) as task_form:
            self.assertFalse(
                task_form.sale_warning_text,
                "No warning should be displayed on a task without customer.",
            )
            task_form.partner_id = self.partner_with_warning
            self.assertEqual(
                task_form.sale_warning_text,
                self.partner_warning,
                "The warning should be displayed as soon as the customer is set in the form.",
            )
            task_form.partner_id = self.child_partner_with_warning
            self.assertEqual(
                task_form.sale_warning_text,
                self.child_partner_warning,
                "The warning should be updated when the customer changes in the form.",
            )

    def test_project_template_create_wizard_sale_warning_text(self):
        with Form(
            self.env['project.template.create.wizard'].with_context(template_id=self.project_template.id),
            view='project.project_project_view_form_simplified_template',
        ) as wizard_form:
            wizard_form.name = 'Project From Template'
            self.assertFalse(
                wizard_form.sale_warning_text,
                "No warning should be displayed before a customer is set.",
            )
            wizard_form.partner_id = self.partner_with_warning
            self.assertEqual(
                wizard_form.sale_warning_text,
                self.partner_warning,
                "The wizard should display the sale warning of the selected customer.",
            )
            wizard_form.partner_id = self.child_partner_with_warning
            self.assertEqual(
                wizard_form.sale_warning_text,
                self.child_partner_warning,
                "The warning should be updated when the customer changes in the wizard.",
            )

    def test_sale_warning_text_without_warning_group(self):
        self.group_user.sudo()._remove_group(self.group_warning_sale)
        project = self.env['project.project'].create({
            'name': 'Project',
            'allow_billable': True,
            'partner_id': self.child_partner_with_warning.id,
        })
        task = self.env['project.task'].create({
            'name': 'Task',
            'project_id': project.id,
            'partner_id': self.child_partner_with_warning.id,
        })
        wizard = self.env['project.template.create.wizard'].create({
            'name': 'Project From Template',
            'template_id': self.project_template.id,
            'partner_id': self.child_partner_with_warning.id,
        })
        self.assertFalse(
            project.sale_warning_text,
            "No warning should be displayed on the project without the sale warning group.",
        )
        self.assertFalse(
            task.sale_warning_text,
            "No warning should be displayed on the task without the sale warning group.",
        )
        self.assertFalse(
            wizard.sale_warning_text,
            "No warning should be displayed in the wizard without the sale warning group.",
        )
