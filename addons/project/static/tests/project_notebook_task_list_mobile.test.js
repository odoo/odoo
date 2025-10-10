import { beforeEach, expect, describe, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

import { defineProjectModels, ProjectProject, ProjectTask } from "./project_models";

defineProjectModels();

describe.current.tags("mobile");

beforeEach(() => {
    ProjectProject._records = [
        {
            id: 5,
            name: "Project One",
        },
    ];

    ProjectTask._records = [
        {
            id: 1,
            name: "task one",
            project_id: 5,
            closed_subtask_count: 1,
            closed_depend_on_count: 1,
            subtask_count: 4,
            child_ids: [2, 3, 4, 7],
            depend_on_ids: [5, 6],
            state: "04_waiting_normal",
        },
        {
            id: 2,
            name: "task two",
            project_id: 5,
            parent_id: 1,
            closed_subtask_count: 0,
            subtask_count: 0,
            child_ids: [],
            depend_on_ids: [],
            state: "03_approved",
        },
        {
            id: 3,
            name: "task three",
            project_id: 5,
            parent_id: 1,
            closed_subtask_count: 0,
            subtask_count: 0,
            child_ids: [],
            depend_on_ids: [],
            state: "02_changes_requested",
        },
        {
            id: 4,
            name: "task four",
            project_id: 5,
            parent_id: 1,
            closed_subtask_count: 0,
            subtask_count: 0,
            child_ids: [],
            depend_on_ids: [],
            state: "1_done",
        },
        {
            id: 5,
            name: "task five",
            project_id: 5,
            closed_subtask_count: 0,
            subtask_count: 1,
            child_ids: [6],
            depend_on_ids: [],
            state: "03_approved",
        },
        {
            id: 6,
            name: "task six",
            project_id: 5,
            parent_id: 5,
            closed_subtask_count: 0,
            subtask_count: 0,
            child_ids: [],
            depend_on_ids: [],
            state: "1_canceled",
        },
        {
            id: 7,
            name: "task seven",
            project_id: 5,
            parent_id: 1,
            closed_subtask_count: 0,
            subtask_count: 0,
            child_ids: [],
            depend_on_ids: [],
            state: "01_in_progress",
        },
    ];

    ProjectTask._views = {
        form: `
            <form>
                <field name="name"/>
                <field name="child_ids" widget="subtasks_one2many">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <main>
                                    <field name="name" class="fw-bold fs-5"/>
                                    <field name="project_id" widget="project"/>
                                    <field name="state"/>
                                </main>
                            </t>
                        </templates>
                    </kanban>
                </field>
                <field name="depend_on_ids" widget="notebook_task_one2many">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <main>
                                    <field name="name" class="fw-bold fs-5"/>
                                    <field name="project_id" widget="project"/>
                                    <field name="state"/>
                                </main>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>
        `,
        search: `<search/>`,
    };
});

test("test open subtask in form view instead of form view dialog", async () => {
    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        name: "Tasks",
        res_model: "project.task",
        type: "ir.actions.act_window",
        res_id: 1,
        views: [[false, "form"]],
    });

    expect("div[name='name'] input").toHaveValue("task one");
    expect("div[name='child_ids'] .o_kanban_record:not(.o_kanban_ghost)").toHaveCount(4, {
        message:
            "The subtasks list should display all subtasks by default, thus we are looking for 4 in total",
    });

    await click("div[name='child_ids'] .o_kanban_record:first-child");
    await animationFrame();
    expect(document.body).not.toHaveClass("modal-open");
    expect("div[name='name'] input").toHaveValue("task two");
});

test("test open task dependencies in form view instead of form view dialog", async () => {
    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        name: "Tasks",
        res_model: "project.task",
        type: "ir.actions.act_window",
        res_id: 1,
        views: [[false, "form"]],
    });

    expect("div[name='name'] input").toHaveValue("task one");
    expect("div[name='depend_on_ids'] .o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2, {
        message:
            "The depend on tasks list should display all blocking tasks by default, thus we are looking for 2 in total",
    });
    await click("div[name='depend_on_ids'] .o_kanban_record:first-child");
    await animationFrame();
    expect(document.body).not.toHaveClass("modal-open");
    expect("div[name='name'] input").toHaveValue("task five");
});
