# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import Command
from odoo.tests import Form, tagged, TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user

@tagged('post_install', '-at_install')
class TestWorksheet(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.worksheet_template = cls.env['worksheet.template'].create({
            'name': 'New worksheet',
            'res_model': 'project.task',
        })
        cls.fsm_project = cls.env['project.project'].create({
            'name': 'Field Service',
            'is_fsm': True,
            'company_id': cls.env.company.id,
        })
        cls.second_fsm_project = cls.env['project.project'].create({
            'name': 'Field Service',
            'is_fsm': True,
            'allow_worksheets': True,
            'worksheet_template_id': cls.worksheet_template.id,
            'company_id': cls.env.company.id,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Costumer A'})
        cls.task = cls.env['project.task'].create({
            'name': 'Fsm task',
            'project_id': cls.fsm_project.id,
            'partner_id': cls.partner.id,
        })

    def test_project_worksheet_template_propagation(self):
        """
            1) Test project template propagation when changing task project with empty worksheet template
            2) Test project template propagation when creating new task
        """
        self.task.write({
            'worksheet_template_id': False,
        })
        self.assertFalse(self.task.worksheet_template_id)

        self.task.write({
            'project_id': self.second_fsm_project.id,
        })

        self.assertEqual(self.task.worksheet_template_id, self.second_fsm_project.worksheet_template_id)
        secondTask = self.env['project.task'].create({
            'name': 'Fsm task',
            'project_id': self.second_fsm_project.id,
            'partner_id': self.partner.id,
        })
        self.assertEqual(secondTask.worksheet_template_id, self.second_fsm_project.worksheet_template_id)
        self.assertTrue(secondTask.allow_worksheets)

    def test_subtasks_worksheet_template_id_duplicate(self):
        self.task.write({
            'project_id': self.second_fsm_project.id,
            'child_ids': [
                Command.create({
                    'name': '%s: substask1' % (self.task.name,),
                }),
                Command.create({
                    'name': '%s: subtask2' % (self.task.name,),
                    'worksheet_template_id': self.worksheet_template.id
                }),
            ],
        })

        subtask1_worksheet_template_id = self.task.child_ids[0].worksheet_template_id
        subtask2_worksheet_template_id = self.task.child_ids[1].worksheet_template_id
        task_copy = self.task.copy()
        subtask1_copy_worksheet_template_id = task_copy.child_ids[0].worksheet_template_id
        subtask2_copy_worksheet_template_id = task_copy.child_ids[1].worksheet_template_id
        self.assertEqual(subtask1_copy_worksheet_template_id, subtask1_worksheet_template_id, "When duplicating a task, subtasks should keep the same worksheet template that we set before.")
        self.assertEqual(subtask2_copy_worksheet_template_id, subtask2_worksheet_template_id, "When duplicating a task, subtasks should keep the same worksheet template that we set before.")

    def test_project_worksheets(self):
        fsm_project = self.env['project.project'].create({
            'name': 'Test FSM Project',
            'is_fsm': True,
            'company_id': self.env.company.id,
        })
        self.assertTrue(fsm_project.allow_worksheets, "By default, worksheet should be enable for Fsm project")

    def test_archive_worksheet_template(self):
        self.fsm_project.worksheet_template_id = self.worksheet_template
        self.worksheet_template.action_archive()
        self.assertFalse(self.fsm_project.worksheet_template_id, "When archiving a worksheet template, it should be removed from the project")

    def test_report_arch_invisible_field(self):
        report_view = self.worksheet_template.report_view_id
        self.assertXMLEqual(report_view.arch, f"""
         <t t-name="{report_view.name}">
           <div>
             <div>
               <div>
                 <div class="row mb-2 bg-light bg-opacity-25 border-top border-bottom pt-2 pb-2" style="page-break-inside: avoid">
                   <div t-att-class="('col-5' if report_type == 'pdf' else 'col-lg-3 col-12') + ' fw-bold'">Comments</div>
                   <div placeholder="Add details about your intervention..." t-att-class="'col-7' if report_type == 'pdf' else 'col-lg-9 col-12'" t-field="worksheet.x_comments"/>
                 </div>
               </div>
             </div>
           </div>
         </t>
        """)

        form_view = self.env["ir.ui.view"].search([("model", "=", self.worksheet_template.model_id.model), ("type", "=", "form")], limit=1)[0]
        self.env["ir.ui.view"].create({
            "name": "test inherit",
            "inherit_id": form_view.id,
            "model": form_view.model,
            "mode": "extension",
            "arch": """
                <xpath expr="//field[@name='x_comments']" position="attributes">
                    <attribute name="invisible">1</attribute>
                </xpath>
            """
        })

        self.worksheet_template._generate_qweb_report_template(form_view.id)
        self.assertXMLEqual(report_view.arch, f"""
         <t t-name="{report_view.name}">
           <div>
             <div>
               <div/>
             </div>
           </div>
         </t>
        """)

    def test_open_worksheet_wizard_condition(self):
        """
        This test ensures that the wizard is only open when needed. The conditions for it to open are the following ones:
        - There are no worksheets in the db (and)
        - The only available worksheet template is the template called 'Default Worksheet' (and)
        - The user must have the system admin rights
        """
        self.env['worksheet.template'].search([]).action_archive()
        template_vals = {
            'name': 'Default Worksheet',
            'res_model': 'project.task',
        }
        default_template = self.env['worksheet.template'].create(template_vals)
        self.task.worksheet_template_id = default_template
        action_name = self.task.worksheet_template_id.action_id.sudo().read()[0]['name']

        action_wizard = self.task.action_fsm_worksheet()
        self.assertEqual(action_wizard['name'], 'Explore Worksheets Using an Example Template', 'The expected return value of the method is the action wizard.')

        new_template = self.env['worksheet.template'].create(template_vals)
        action_wizard = self.task.action_fsm_worksheet()
        self.assertEqual(action_wizard['name'], action_name, 'There is more than one template: the expected return value of the method is the action of the template.')

        new_template.unlink()
        project_manager = mail_new_test_user(self.env, 'Project admin', groups='project.group_project_manager')
        action_wizard = self.task.with_user(project_manager).action_fsm_worksheet()
        self.assertEqual(action_wizard['name'], action_name, 'The current user is not a system admin : the expected return value of the method is the action of the template.')

        self.env[default_template.sudo().model_id.model].create({'x_project_task_id': self.task.id})
        action_wizard = self.task.action_fsm_worksheet()
        self.assertEqual(action_wizard['name'], action_name, 'There is at least one worksheet created with this template: the expected return value of the method is the action of the template.')

    def test_generated_template_from_wizard(self):
        """
        This test ensures that the template generated from the wizard is correctly created.
        """
        wizard = self.env['worksheet.template.load.wizard'].create({'task_id': self.task.id})
        default_template = self.env['worksheet.template'].create({
            'name': 'Default Worksheet',
            'res_model': 'project.task',
        })
        self.task.worksheet_template_id = default_template
        wizard.action_generate_new_template()
        self.assertNotEqual(default_template, self.task.worksheet_template_id, 'A new template should be set on the task.')
        form_views = self.env['ir.ui.view'].search([('model', '=', self.task.worksheet_template_id.model_id.model), ('type', '=', 'form')], limit=3)
        self.assertEqual(2, len(form_views), "Only two form views should have been created for this model")
        self.assertEqual(form_views[0], form_views[1].inherit_id, 'Two views should have been created, and the second should inherit the first one.')
        fields = self.task.worksheet_template_id.model_id.field_id
        extra_fields = fields.filtered(lambda f: f.name in ['x_intervention_type', 'x_description', 'x_manufacturer', 'x_checkbox', 'x_serial_number', 'x_date', 'x_worker_signature'])
        self.assertEqual(7, len(extra_fields), 'The extra fields should all have been created.')

    def test_send_reports_in_batches(self):
        """
        This test ensures that implementation of sending batches in reports is working.
        """
        tasks = self.env['project.task'].create([
            {
                'name': 'Fsm task-report-1',
                'project_id': self.fsm_project.id,
                'partner_id': self.partner.id,
                'worksheet_template_id': self.worksheet_template.id,
            },
            {
                'name': 'Fsm task-report-2',
                'project_id': self.fsm_project.id,
                'partner_id': self.partner.id,
            },
        ])
        task_1, task_2 = tasks
        self.env[self.worksheet_template.sudo().model_id.model].sudo().create({
            'x_project_task_id': task_1.id,
        })
        self.assertEqual(
            task_2.action_send_report()['params']['message'],
            'There are no reports to send.', 'Task with no report raise a toast message',
        )
        self.assertEqual(
            tasks.action_send_report()["context"]["report_action"]["context"]["default_res_ids"],
            task_1.ids,
            'Task with report is being sent others are ignored',
        )
        task_2.write({
            'worksheet_template_id': self.worksheet_template.id,
        })
        self.env[self.worksheet_template.sudo().model_id.model].create({
            'x_project_task_id': task_2.id,
        })
        self.assertEqual(
            tasks.action_send_report()["context"]["report_action"]["context"]["default_res_ids"],
            tasks.ids,
            'Both the tasks with reports are being sent',
        )

    def test_set_worksheet_template_with_multi_company(self):
        """
            Verify the worksheet template based on the project company.
            Steps
                - Create a new company (TestCompany1)
                - Create a worksheet template and set up a company (TestCompany1)
                - Create project
                - Verify the worksheet template and the project company.
                - Set TestCompany1 to the project.
                - Again verify the worksheet template and the project company.
        """

        test_company = self.env['res.company'].create({
            'name': 'TestCompany1',
            'country_id': self.env.ref('base.be').id,
        })
        self.env['worksheet.template'].create({
            'name': 'test worksheet',
            'res_model': 'project.task',
            'company_id': test_company.id,
        })

        with Form(self.env['project.project']) as project_form:
            project_form.name = "Test Project"
            project_form.allow_worksheets = True
            self.assertEqual(project_form.company_id, project_form.worksheet_template_id.company_id)
            project_form.company_id = test_company
            self.assertEqual(project_form.company_id, project_form.worksheet_template_id.company_id)

    def test_report_arch_file_field(self):
        report_view = self.worksheet_template.report_view_id

        def _create_field(field_name, field_type, field_description):
            self.env["ir.model.fields"].create({
                "field_description": field_description,
                "name": field_name,
                "ttype": field_type,
                "model": report_view.name,
                "model_id": self.env["ir.model"]._get(report_view.name).id,
                "state": "manual",
            })
        _create_field('x_new_file', 'binary', 'New File')
        _create_field('x_new_file_filename', 'char', 'New File char')

        self.assertXMLEqual(report_view.arch, f"""
            <t t-name="{report_view.name}">
                <div>
                    <div>
                        <div>
                            <div class="row mb-2 bg-light bg-opacity-25 border-top border-bottom pt-2 pb-2" style="page-break-inside: avoid">
                                <div t-att-class="('col-5' if report_type == 'pdf' else 'col-lg-3 col-12') + ' fw-bold'">Comments</div>
                                <div placeholder="Add details about your intervention..." t-att-class="'col-7' if report_type == 'pdf' else 'col-lg-9 col-12'" t-field="worksheet.x_comments"/>
                            </div>
                        </div>
                    </div>
                </div>
            </t>
        """)

        form_view = self.env["ir.ui.view"].search([("model", "=", self.worksheet_template.model_id.model), ("type", "=", "form")], limit=1)[0]
        self.env["ir.ui.view"].create({
            "name": "test file field",
            "inherit_id": form_view.id,
            "model": form_view.model,
            "mode": "extension",
            "arch": """
                <xpath expr="//field[@name='x_comments']" position="after">
                    <field name="x_new_file" widget="file" filename="x_new_file_filename"/>
                    <field name="x_new_file_filename" invisible="1"/>
                </xpath>
            """
        })

        self.worksheet_template._generate_qweb_report_template(form_view.id)
        self.assertXMLEqual(report_view.arch, f"""
            <t t-name="{report_view.name}">
                <div>
                    <div>
                        <div>
                            <div class="row mb-2 bg-light bg-opacity-25 border-top border-bottom pt-2 pb-2" style="page-break-inside: avoid">
                                <div t-att-class="('col-5' if report_type == 'pdf' else 'col-lg-3 col-12') + ' fw-bold'">Comments</div>
                                <div placeholder="Add details about your intervention..." t-att-class="'col-7' if report_type == 'pdf' else 'col-lg-9 col-12'" t-field="worksheet.x_comments"/>
                            </div>
                            <div class="row mb-2" style="page-break-inside: avoid">
                                <div t-att-class="('col-5' if report_type == 'pdf' else 'col-lg-3 col-12') + ' fw-bold'">New File</div>
                                <div widget="file" filename="x_new_file_filename" t-att-class="'col-7' if report_type == 'pdf' else 'col-lg-7 col-12'" t-field="worksheet.x_new_file_filename"/>
                            </div>
                        </div>
                    </div>
                </div>
            </t>
        """)
