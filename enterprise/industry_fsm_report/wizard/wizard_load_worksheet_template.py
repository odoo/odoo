# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WorksheetTemplateLoad(models.TransientModel):
    _name = 'worksheet.template.load.wizard'
    _description = 'Load the worksheet template'

    task_id = fields.Many2one('project.task', "Task", required=True)

    def action_generate_new_template(self):
        new_template = self.env['worksheet.template'].sudo().create({
            'name': 'Device Installation and Maintenance',
            'res_model': 'project.task',
        })
        new_template._create_demo_data_fsm(model_id=new_template.model_id.id)
        default_form_view = self.env['ir.ui.view'].sudo().search([('model', '=', new_template.model_id.model), ('type', '=', 'form')], limit=1)
        extend_view_id = self.env["ir.ui.view"].sudo().create({
            "type": "form",
            "name": 'template_view_' + new_template.name.replace(' ', '_'),
            "model": new_template.model_id.model,
            "inherit_id": default_form_view.id,
            "arch": """
                    <xpath expr="//form/sheet" position="replace">
                        <sheet>
                            <group invisible="context.get('studio') or context.get('default_x_project_task_id')">
                                <div class="oe_title">
                                    <h1>
                                        <field name="x_project_task_id" domain="[('is_fsm', '=', True)]" readonly="1"/>
                                    </h1>
                                </div>
                            </group>
                            <group class="o_fsm_worksheet_form">
                                <field name="x_name"/>
                                <field name="x_manufacturer" options="{'no_create':true, 'no_open':true}"/>
                                <field name="x_serial_number"/>
                                <field name="x_intervention_type" widget="radio"/>
                                <field name="x_description"/>
                                <field name="x_checkbox"/>
                                <field name="x_date"/>
                                <field name="x_worker_signature" widget="signature"/>
                            </group>
                        </sheet>
                    </xpath>
                    """,
        }).id
        new_template._generate_qweb_report_template(form_view_id=extend_view_id)
        self.task_id.worksheet_template_id = new_template
        return self.task_id.open_fsm_worksheet()

    def action_open_template(self):
        return self.task_id.open_fsm_worksheet()
