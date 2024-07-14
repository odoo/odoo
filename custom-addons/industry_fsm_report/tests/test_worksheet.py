# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.tests import tagged, TransactionCase

@tagged('post_install', '-at_install')
class TestWorksheet(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.worksheet_template = cls.env['worksheet.template'].create({
            'name': 'New worksheet',
            'color': 4,
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
        })

        self.first_subtask = self.env['project.task'].create({
            'parent_id': self.task.id,
            'name': '%s: substask1' % (self.task.name,),
        })

        self.second_subtask = self.env['project.task'].create({
            'parent_id': self.task.id,
            'name': '%s: subtask2' % (self.task.name,),
            'worksheet_template_id': self.worksheet_template.id
        })

        subtask1_worksheet_template_id = self.second_fsm_project.tasks[-1].child_ids[0].worksheet_template_id
        subtask2_worksheet_template_id = self.second_fsm_project.tasks[-1].child_ids[1].worksheet_template_id
        task_copy = self.second_fsm_project.tasks[-1].copy()
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

    def test_report_arch_invisible_field(self):
        report_view = self.worksheet_template.report_view_id
        self.assertXMLEqual(report_view.arch, f"""
         <t t-name="{report_view.name}">
           <div>
             <div>
               <div>
                 <div class="row mb-3" style="page-break-inside: avoid">
                   <div t-att-class="('col-5' if report_type == 'pdf' else 'col-lg-5 col-12') + ' font-weight-bold'">Comments</div>
                   <div placeholder="Add details about your intervention..." t-att-class="'col-7' if report_type == 'pdf' else 'col-lg-7 col-12'" t-field="worksheet.x_comments"/>
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
