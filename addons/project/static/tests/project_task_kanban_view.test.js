import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, waitFor } from "@odoo/hoot-dom";

import { mountView, onRpc } from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectTask } from "./project_models";

defineProjectModels();
describe.current.tags("desktop");

const viewParams = {
    resModel: "project.task",
    type: "kanban",
    arch: `
        <kanban default_group_by="stage_id" js_class="project_task_kanban">
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

test("project.task (kanban): toggle sub-tasks", async () => {
    ProjectTask._records = [
        {
            id: 1,
            project_id: 1,
            name: "Task 1",
            stage_id:  1,
            display_in_project: true,
        },
        {
            id: 2,
            project_id: 1,
            name: "Task 2",
            stage_id:  1,
            display_in_project: false,
        }
    ];
    await mountView(viewParams);
    expect(".o_kanban_record").toHaveCount(1);
    expect(".o_control_panel_navigation button i.fa-sliders").toHaveCount(1);
    await click(".o_control_panel_navigation button i.fa-sliders");
    await waitFor("span.o-dropdown-item");
    expect("span.o-dropdown-item").toHaveText("Show Sub-Tasks");
    await click("span.o-dropdown-item");
    await animationFrame();
    expect(".o_kanban_record").toHaveCount(2);
});
