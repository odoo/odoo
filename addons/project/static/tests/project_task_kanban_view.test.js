import { describe, expect, test } from "@odoo/hoot";

import { mountView } from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectTask } from "./project_models";

defineProjectModels();
describe.current.tags("desktop");

test("shadow stages should be displayed in the project Kanban", async () => {
    ProjectTask._records = [];

    await mountView({
        resModel: "project.task",
        type: "kanban",
        arch: `
            <kanban default_group_by="stage_id" js_class="project_task_kanban">
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>
        `,
        context: {
            'active_model': "project.task.type.delete.wizard",
            'default_project_id': 1,
        },
    });

    expect(".o_kanban_header").toHaveCount(1);
    expect(".o_kanban_example_background_container").toHaveCount(1);
});
