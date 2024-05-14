import { models, fields } from "@web/../tests/web_test_helpers";

export class ProjectTask extends models.ServerModel {
    _name = "project.task";

    project_id = fields.Many2one({ relation: "project.project", searchable: true, string: "Project" });
    milestone_id = fields.Many2one({ relation: "project.milestone", searchable: true, string: "Milestone" });

    _views = {
        ["kanban,false"]: `
            <kanban js_class="project_task_kanban">
                <field name="subtask_count"/>
                <field name="closed_subtask_count"/>
                <field name="project_id"/>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="display_name" widget="name_with_subtask_count"/>
                            <field name="user_ids" invisible="1" widget="many2many_avatar_user"/>
                            <field name="child_ids" invisible="1"/>
                            <field name="state" invisible="1" widget="project_task_state_selection"/>
                            <t t-if="record.project_id.raw_value and record.subtask_count.raw_value">
                                <widget name="subtask_counter"/>
                            </t>
                            <widget name="subtask_kanban_list" />
                        </div>
                    </t>
                </templates>
            </kanban>`,
        ["form,false"]: `
            <form>
                <field name="child_ids" widget="subtasks_one2many">
                    <tree editable="bottom">
                        <field name="display_in_project" force_save="1"/>
                        <field name="project_id" widget="project"/>
                        <field name="name"/>
                    </tree>
                </field>
            </form>`,
        ["list,false"]: `<tree js_class="project_task_list"/>`,
    };
}
