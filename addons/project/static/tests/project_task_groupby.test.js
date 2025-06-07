import { beforeEach, expect, test } from "@odoo/hoot";
import { mountView } from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectTask } from "./project_models";

defineProjectModels();
beforeEach(() => {
    ProjectTask._records = [
        {
            id: 1,
            name: "My task",
            project_id: false,
            user_ids: [],
            date_deadline: false,
        },
    ];
});

test("project.task (tree): check group label for no project", async () => {
    await mountView({
        resModel: "project.task",
        type: "list",
        arch: `<list js_class="project_task_list"/>`,
        groupBy: ["project_id"],
    });
    expect(".o_group_name").toHaveText("🔒 Private (1)");
});

test("project.task (tree): check group label for no assignees", async () => {
    await mountView({
        resModel: "project.task",
        type: "list",
        arch: `<list js_class="project_task_list"/>`,
        groupBy: ["user_ids"],
    });
    expect(".o_group_name").toHaveText("👤 Unassigned (1)");
});

test("project.task (tree): check group label for no deadline", async () => {
    await mountView({
        resModel: "project.task",
        type: "list",
        arch: `<list js_class="project_task_list"/>`,
        groupBy: ["date_deadline"],
    });
    expect(".o_group_name").toHaveText("None (1)");
});

test("project.task (kanban): check group label for no project", async () => {
    await mountView({
        resModel: "project.task",
        type: "kanban",
        arch: `
            <kanban js_class="project_task_kanban" default_group_by="project_id">
                <templates>
                    <t t-name="card"/>
                </templates>
            </kanban>
        `,
    });
    expect(".o_column_title").toHaveText("🔒 Private\n(1)");
});

test("project.task (kanban): check group label for no assignees", async () => {
    await mountView({
        resModel: "project.task",
        type: "kanban",
        arch: `
            <kanban js_class="project_task_kanban" default_group_by="user_ids">
                <templates>
                    <t t-name="card"/>
                </templates>
            </kanban>
        `,
    });
    expect(".o_column_title").toHaveText("👤 Unassigned\n(1)");
});

test("project.task (kanban): check group label for no deadline", async () => {
    await mountView({
        resModel: "project.task",
        type: "kanban",
        arch: `
            <kanban js_class="project_task_kanban" default_group_by="date_deadline">
                <templates>
                    <t t-name="card"/>
                </templates>
            </kanban>
        `,
    });
    expect(".o_column_title").toHaveText("None\n(1)");
});

test("project.task (pivot): check group label for no project", async () => {
    await mountView({
        resModel: "project.task",
        type: "kanban",
        arch: `
            <pivot js_class="project_pivot">
                <field name="project_id" type="row"/>
            </pivot>
        `,
    });
    expect("tr:nth-of-type(2) .o_pivot_header_cell_closed").toHaveText("Private");
});

test("project.task (pivot): check group label for no assignees", async () => {
    await mountView({
        resModel: "project.task",
        type: "kanban",
        arch: `
            <pivot js_class="project_pivot">
                <field name="user_ids" type="row"/>
            </pivot>
        `,
    });
    expect("tr:nth-of-type(2) .o_pivot_header_cell_closed").toHaveText("Unassigned");
});

test("project.task (pivot): check group label for no deadline", async () => {
    await mountView({
        resModel: "project.task",
        type: "kanban",
        arch: `
            <pivot js_class="project_pivot">
                <field name="date_deadline" type="row"/>
            </pivot>
        `,
    });
    expect("tr:nth-of-type(2) .o_pivot_header_cell_closed").toHaveText("None");
});
