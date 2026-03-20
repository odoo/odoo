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
    expect(".o_column_quick_create.o_quick_create_folded").toHaveCount(1, {
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
    expect(".o_column_quick_create.o_quick_create_folded").toHaveCount(0, {
        message: "Add column button should not be visible",
    });
});
