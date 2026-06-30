import { beforeEach, expect, describe, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountView } from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectProject, ProjectTask } from "./project_models";

defineProjectModels();

describe.current.tags("desktop");

beforeEach(() => {
    ProjectProject._records = [
        {
            id:5,
            name: "Project One"
        },
    ];

    ProjectTask._records = [
        {
            id: 1,
            name: 'task one',
            project_id: 5,
            closed_subtask_count: 1,
            closed_depend_on_count: 1,
            subtask_count: 4,
            child_ids: [2, 3, 4, 7],
            depend_on_ids: [5,6],
            state: '04_waiting_normal',
        },
        {
            name: 'task two',
            parent_id: 1,
            closed_subtask_count: 0,
            subtask_count: 0,
            child_ids: [],
            depend_on_ids: [],
            state: '03_approved'
        },
        {
            name: 'task three',
            parent_id: 1,
            closed_subtask_count: 0,
            subtask_count: 0,
            child_ids: [],
            depend_on_ids: [],
            state: '02_changes_requested'
        },
        {
            name: 'task four',
            parent_id: 1,
            closed_subtask_count: 0,
            subtask_count: 0,
            child_ids: [],
            depend_on_ids: [],
            state: '1_done'
        },
        {
            name: 'task five',
            closed_subtask_count: 0,
            subtask_count: 1,
            child_ids: [6],
            depend_on_ids: [],
            state: '03_approved'
        },
        {
            name: 'task six',
            parent_id: 5,
            closed_subtask_count: 0,
            subtask_count: 0,
            child_ids: [],
            depend_on_ids: [],
            state: '1_canceled'
        },
        {
            name: 'task seven',
            parent_id: 1,
            closed_subtask_count: 0,
            subtask_count: 0,
            child_ids: [],
            depend_on_ids: [],
            state: '01_in_progress',
        },
    ];

    ProjectTask._views = {
        form: `
            <form>
                <field name="closed_depend_on_count" invisible="1"/>
                <field name="child_ids" widget="subtasks_one2many">
                    <list editable="bottom">
                        <field name="display_in_project" force_save="1"/>
                        <field name="project_id" widget="project"/>
                        <field name="name"/>
                        <field name="state"/>
                    </list>
                </field>
                <field name="depend_on_ids" widget="notebook_task_one2many" context="{ 'closed_X2M_count': closed_depend_on_count }">
                    <list editable="bottom">
                        <field name="display_in_project" force_save="1"/>
                        <field name="project_id" widget="project"/>
                        <field name="name"/>
                        <field name="state"/>
                    </list>
                </field>
            </form>
        `,
    };
});

test("test Project Task Calendar Popover with task_stage_with_state_selection widget", async () => {
    await mountView({
        resModel: "project.task",
        type: "form",
        resId: 1,
    });

    expect('div[name="child_ids"] .o_data_row').toHaveCount(4, {
        message: "The subtasks list should display all subtasks by default, thus we are looking for 4 in total"
    });
    expect('div[name="depend_on_ids"] .o_data_row').toHaveCount(2, {
        message: "The depend on tasks list should display all blocking tasks by default, thus we are looking for 2 in total"
    });

    expect("div[name='child_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button").toHaveText("Hide closed tasks");
    expect("div[name='depend_on_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button").toHaveText("Hide closed tasks");

    await click("div[name='child_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button");
    await animationFrame();

    expect("div[name='child_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button").toHaveText("Show closed tasks");
    expect("div[name='depend_on_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button").toHaveText("Hide closed tasks");

    expect('div[name="child_ids"] .o_data_row').toHaveCount(3, {
        message: "The subtasks list should only display the open subtasks of the task, in this case 3"
    });
    expect('div[name="depend_on_ids"] .o_data_row').toHaveCount(2, {
        message: "The depend on tasks list should still display all blocking tasks, in this case 2"
    });

    await click("div[name='depend_on_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button");
    await animationFrame();

    expect("div[name='child_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button").toHaveText("Show closed tasks");
    expect("div[name='depend_on_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button").toHaveText("1 closed tasks");

    expect('div[name="child_ids"] .o_data_row').toHaveCount(3, {
        message: "The subtasks list should only display the open subtasks of the task, in this case 3"
    });
    expect('div[name="depend_on_ids"] .o_data_row').toHaveCount(1, {
        message: "The depend on tasks list should only display open tasks, in this case 1"
    });
});
