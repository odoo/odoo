import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { click, edit, queryOne } from "@odoo/hoot-dom";
import { Command, mountView, MockServer, onRpc } from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectTask } from "./project_models";

defineProjectModels();

describe.current.tags("desktop");

beforeEach(() => {
    ProjectTask._records = [
        {
            id: 1,
            name: "Task 1 (Project 1)",
            project_id: 1,
            child_ids: [2, 3, 4, 7],
            closed_subtask_count: 1,
            subtask_count: 4,
            user_ids: [7],
            state: "01_in_progress",
        },
        {
            id: 2,
            name: "Task 2 (Project 1)",
            project_id: 1,
            parent_id: 1,
            child_ids: [],
            closed_subtask_count: 0,
            subtask_count: 0,
            state: "03_approved",
        },
        {
            id: 3,
            name: "Task 3 (Project 1)",
            project_id: 1,
            parent_id: 1,
            closed_subtask_count: 0,
            subtask_count: 0,
            child_ids: [],
            state: "02_changes_requested",
        },
        {
            id: 4,
            name: "Task 4 (Project 1)",
            project_id: 1,
            parent_id: 1,
            closed_subtask_count: 0,
            subtask_count: 0,
            child_ids: [],
            state: "1_done",
        },
        {
            id: 5,
            name: "Task 5 (Private)",
            closed_subtask_count: 0,
            subtask_count: 1,
            child_ids: [6],
            state: "03_approved",
        },
        {
            id: 6,
            name: "Task 6 (Private)",
            parent_id: 5,
            closed_subtask_count: 0,
            subtask_count: 0,
            child_ids: [],
            state: "1_canceled",
        },
        {
            id: 7,
            name: "Task 7 (Project 1)",
            project_id: 1,
            parent_id: 1,
            closed_subtask_count: 0,
            subtask_count: 0,
            child_ids: [],
            state: "01_in_progress",
            user_ids: [7],
        },
        {
            id: 8,
            name: "Task 1 (Project 2)",
            project_id: 2,
            child_ids: [],
        },
    ];
    ProjectTask._views = {
        kanban: `
            <kanban js_class="project_task_kanban">
                <field name="subtask_count"/>
                <field name="project_id"/>
                <field name="closed_subtask_count"/>
                <field name="child_ids"/>
                <field name="user_ids"/>
                <field name="state"/>
                <templates>
                    <t t-name="card">
                        <div>
                            <field name="display_name" widget="name_with_subtask_count"/>
                            <t t-if="record.project_id.raw_value and record.subtask_count.raw_value">
                                <widget name="subtask_counter"/>
                            </t>
                            <widget name="subtask_kanban_list"/>
                        </div>
                    </t>
                </templates>
            </kanban>
        `,
        form: `
            <form>
                <field name="child_ids" widget="subtasks_one2many">
                    <list editable="bottom">
                        <field name="project_id" widget="project"/>
                        <field name="name"/>
                    </list>
                </field>
            </form>
        `,
    };
});

test("project.task (kanban): check subtask list", async () => {
    await mountView({
        resModel: "project.task",
        type: "kanban",
    });

    expect(".o_field_name_with_subtask_count:contains('(1/4 sub-tasks)')").toHaveCount(1, {
        message:
            "Task title should also display the number of (closed) sub-tasks linked to the task",
    });
    expect(".subtask_list_button").toHaveCount(1, {
        message:
            "Only kanban boxes of parent tasks having open subtasks should have the drawdown button, in this case this is 1",
    });
    expect(".subtask_list").toHaveCount(0, {
        message: "If the drawdown button is not clicked, the subtasks list should be hidden",
    });

    await click(".subtask_list_button");
    await animationFrame();
    expect(".subtask_list").toHaveCount(1, {
        message:
            "Clicking on the button should make the subtask list render, in this case we are expectig 1 list",
    });
    expect(".subtask_list_row").toHaveCount(3, {
        message: "The list rendered should show the open subtasks of the task, in this case 3",
    });
    expect(".subtask_state_widget_col").toHaveCount(3, {
        message:
            "Each of the list's rows should have 1 state widget, thus we are looking for 3 in total",
    });
    expect(".subtask_user_widget_col").toHaveCount(3, {
        message:
            "Each of the list's rows should have 1 user widgets, thus we are looking for 3 in total",
    });
    expect(".subtask_name_col").toHaveCount(3, {
        message:
            "Each of the list's rows should display the subtask's name, thus we are looking for 3 in total",
    });

    await click(".subtask_list_button");
    await animationFrame();
    expect(".subtask_list").toHaveCount(0, {
        message:
            "If the drawdown button is clicked again, the subtasks list should be hidden again",
    });
});

test("project.task (kanban): check closed subtask count update", async () => {
    let checkSteps = false;
    onRpc(({ method, model }) => {
        if (checkSteps) {
            expect.step(`${model}/${method}`);
        }
    });
    await mountView({
        resModel: "project.task",
        type: "kanban",
    });
    checkSteps = true;

    expect(queryOne(".subtask_list_button").parentNode).toHaveText("1/4");
    await click(".subtask_list_button");
    await animationFrame();
    const inProgressStatesSelector = `
        .subtask_list
        .o_field_widget.o_field_project_task_state_selection.subtask_state_widget_col
        .o_status:not(.o_status_green,.o_status_bubble)
    `;
    expect(inProgressStatesSelector).toHaveCount(1, {
        message: "The state of the subtask should be in progress",
    });

    await click(inProgressStatesSelector);
    await animationFrame();
    await click(".project_task_state_selection_menu .fa-check-circle");
    await animationFrame();
    expect(inProgressStatesSelector).toHaveCount(0, {
        message: "The state of the subtask should no longer be in progress",
    });
    expect.verifySteps([
        "project.task/web_read",
        "project.task/onchange",
        "project.task/web_save",
    ]);
});

test("project.task (kanban): check subtask creation", async () => {
    let checkSteps = false;
    onRpc(({ args, method, model }) => {
        if (checkSteps) {
            expect.step(`${model}/${method}`);
        }
        if (model === "project.task" && method === "create") {
            const [{ display_name, parent_id }] = args[0];
            expect(display_name).toBe("New Subtask");
            expect(parent_id).toBe(1);
            const newSubtaskId = MockServer.env["project.task"].create({
                name: display_name,
                parent_id,
                state: "01_in_progress",
            });
            MockServer.env["project.task"].write(parent_id, {
                child_ids: [Command.link(newSubtaskId)],
            });
            return [newSubtaskId];
        }
    });
    await mountView({
        resModel: "project.task",
        type: "kanban",
    });
    checkSteps = true;

    expect(queryOne(".subtask_list_button").parentNode).toHaveText("1/4");
    await click(".subtask_list_button");
    await animationFrame();
    await click(".subtask_create");
    await animationFrame();
    await click(".subtask_create_input input");
    await edit("New Subtask", { confirm: "enter" });
    await animationFrame();
    expect(".subtask_list_row").toHaveCount(4, {
        message:
            "The subtasks list should now display the subtask created on the card, thus we are looking for 4 in total",
    });
    expect.verifySteps([
        "project.task/web_read",
        "project.task/create",
        "project.task/web_read",
    ]);
});

test("project.task (form): check that the subtask of another project can be added", async () => {
    await mountView({
        resModel: "project.task",
        resId: 7,
        type: "form",
    });

    await click(".o_field_x2many_list_row_add a");
    await animationFrame();
    await click(".o_field_project input");
    await animationFrame();
    await click(".o_field_project li");
    await animationFrame();
    await click(".o_field_project input");
    await edit("aaa");
    await click(".o_form_button_save");
    await animationFrame();
    expect(".o_field_project").toHaveText("Project 1");
});

test("project.task (form): check focus on new subtask's name", async () => {
    await mountView({
        resModel: "project.task",
        type: "form",
    });

    await click(".o_field_x2many_list_row_add a");
    await animationFrame();
    expect(".o_field_char input").toBeFocused({
        message: "Upon clicking on 'Add a line', the new subtask's name should be focused.",
    });
});
