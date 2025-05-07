import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";

import { mountView, onRpc } from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectTask } from "./project_models";

defineProjectModels();
describe.current.tags("desktop");

const viewParams = {
    resModel: "project.task",
    type: "kanban",
    arch: `
        <kanban js_class="project_task_kanban">
            <templates>
                <t t-name="card">
                    <field name="name"/>
                </t>
            </templates>
        </kanban>`,
    context: {
        active_model: "project.project",
        default_project_id: 1,
    },
    groupBy: ["stage_id"],
};

test("stages nocontent helper should be displayed in the project Kanban", async () => {
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
            active_model: "project.task.type.delete.wizard",
            default_project_id: 1,
        },
    });

    expect(".o_kanban_header").toHaveCount(1);
    expect(".o_kanban_stages_nocontent").toHaveCount(1);
});

test("quick create button is visible when the user has access rights.", async () => {
    onRpc("has_group", () => true);
    await mountView(viewParams);
    await animationFrame();
    expect(".o_column_quick_create").toHaveCount(1);
});

test("quick create button is not visible when the user not have access rights", async () => {
    onRpc("has_group", () => false);
    await mountView(viewParams);
    await animationFrame();
    expect(".o_column_quick_create").toHaveCount(0);
});
