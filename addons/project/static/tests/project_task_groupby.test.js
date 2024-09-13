import { beforeEach, expect, test } from "@odoo/hoot";
import { mountView, quickCreateKanbanColumn } from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectTask } from "./project_models";

defineProjectModels();

const kanbanViewParams = {
    resModel: "project.task",
    type: "kanban",
    arch: `<kanban default_group_by="stage_id" js_class="project_task_kanban">
                <templates>
                    <t t-name="card"/>
                </templates>
            </kanban>`,
};

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
        ...kanbanViewParams,
        groupBy: ["project_id"],
    });
    expect(".o_column_title").toHaveText("🔒 Private\n(1)");
});

test("project.task (kanban): check group label for no assignees", async () => {
    await mountView({
        ...kanbanViewParams,
        groupBy: ["user_ids"],
    });
    expect(".o_column_title").toHaveText("👤 Unassigned\n(1)");
});

test("project.task (kanban): check group label for no deadline", async () => {
    await mountView({
        ...kanbanViewParams,
        groupBy: ["date_deadline"],
    });
    expect(".o_column_title").toHaveText("None\n(1)");
});

test("project.task (kanban): Can create stage if we are in tasks of specific project", async () => {
    await mountView({
        ...kanbanViewParams,
        context: {
            default_project_id: 1,
        },
    });
    expect(".o_column_quick_create").toHaveCount(1, {
        message: "should have a quick create column",
    });
    expect(".o_kanban_add_column").toHaveCount(1, {
        message: "Add column button should be visible",
    });
    await quickCreateKanbanColumn();
    expect(".o_column_quick_create input").toHaveCount(1, {
        message: "the input should be visible",
    });
});

test("project.task (kanban): Cannot create stage if we are not in tasks of specific project", async () => {
    await mountView({
        ...kanbanViewParams,
    });
    expect(".o_column_quick_create").toHaveCount(0, {
        message: "quick create column should not be visible",
    });
    expect(".o_kanban_add_column").toHaveCount(0, {
        message: "Add column button should not be visible",
    });
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
