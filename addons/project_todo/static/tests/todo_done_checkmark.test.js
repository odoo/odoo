import { test, expect, describe, beforeEach } from "@odoo/hoot";
import { queryFirst, queryAll, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { WebClient } from "@web/webclient/webclient";
import {
    mountView,
    onRpc,
    mountWithCleanup,
    getService,
    contains,
} from "@web/../tests/web_test_helpers";

import { defineTodoModels } from "./todo_test_helpers";
import { ProjectTask } from "./mock_server/mock_models/project_task";

describe.current.tags("desktop");
defineTodoModels();

beforeEach(() => {
    ProjectTask._views = {
        list: `
            <list js_class="todo_list">
                <field name="name" nolabel="1"/>
                <field name="state" widget="todo_done_checkmark" nolabel="1"/>
            </list>`,
        form: `
            <form string="To-do" class="o_todo_form_view" js_class="todo_form">
                <field name="name"/>
                <field name="state" widget="todo_done_checkmark"/>
            </form>`,
        search: `
            <search/>`,
        kanban: `
            <kanban>
                <template>
                    <t t-name="card">
                        <field name="state" widget="todo_done_checkmark"/>
                    </t>
                </template>
            </kanban>
        `,
    };
});

test("Check clicking on todo_done_checkmark in kanban view with initial state is in progress", async () => {
    onRpc("web_save", ({ args }) => {
        expect(args[1].state).toBe("1_done", {
            message: "The task should be marked as done",
        });
        expect.step("web_save");
    });

    await mountView({
        resModel: "project.task",
        type: "kanban",
    });

    const task1 = queryFirst(".o_kanban_record .o_todo_done_button");
    expect(task1).not.toHaveClass("done_button_enabled", {
        message:
            "The checkmark on this task should be displayed as undone as its state is 01_in_progress",
    });
    task1.click();
    await animationFrame();
    expect(task1).toHaveClass("done_button_enabled", {
        message: "The checkmark on this task should be displayed as done as its state is 1_done",
    });
    expect.verifySteps(["web_save"]);
});

test("Check clicking on todo_done_checkmark in kanban view with initial state is done", async () => {
    onRpc("web_save", ({ args }) => {
        expect(args[1].state).toBe("01_in_progress", {
            message: "The task should be in progress",
        });
        expect.step("web_save");
    });

    await mountView({
        resModel: "project.task",
        type: "kanban",
    });

    const task2 = queryAll(".o_kanban_record .o_todo_done_button")[1];
    expect(task2).toHaveClass("done_button_enabled", {
        message: "The checkmark on this task should be displayed as done as its state is 1_done",
    });
    task2.click();
    await animationFrame();
    expect(task2).not.toHaveClass("done_button_enabled", {
        message:
            "The checkmark on this task should be displayed as undone as its state is 01_in_progress",
    });
    expect.verifySteps(["web_save"]);
});

test("Check clicking on todo_done_checkmark in list view with initial state is in progress", async () => {
    onRpc("web_save", ({ args }) => {
        expect(args[1].state).toBe("1_done", {
            message: "The task should be marked as done",
        });
        expect.step("web_save");
    });

    await mountView({
        resModel: "project.task",
        type: "list",
    });

    const task1 = queryFirst(".o_todo_done_button");
    expect(task1).not.toHaveClass("done_button_enabled", {
        message:
            "The checkmark on this task should be displayed as undone as its state is 01_in_progress",
    });
    task1.click();
    await animationFrame();
    expect(task1).toHaveClass("done_button_enabled", {
        message: "The checkmark on this task should be displayed as done as its state is 1_done",
    });
    expect.verifySteps(["web_save"]);
});

test("Check clicking on todo_done_checkmark in list view with initial state is done", async () => {
    onRpc("web_save", ({ args }) => {
        expect(args[1].state).toBe("01_in_progress", {
            message: "The task should be in progress",
        });
        expect.step("web_save");
    });

    await mountView({
        resModel: "project.task",
        type: "list",
    });

    const task2 = queryAll(".o_todo_done_button")[1];
    expect(task2).toHaveClass("done_button_enabled", {
        message: "The checkmark on this task should be displayed as done as its state is 1_done",
    });
    task2.click();
    await animationFrame();
    expect(task2).not.toHaveClass("done_button_enabled", {
        message:
            "The checkmark on this task should be displayed as undone as its state is 01_in_progress",
    });
    expect.verifySteps(["web_save"]);
});

test("Check clicking on todo_done_checkmark in form view with initial state is in progress", async () => {
    onRpc("web_save", ({ args }) => {
        expect(args[1].state).toBe("1_done", {
            message: "The task should be marked as done",
        });
        expect.step("web_save");
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "To-do",
        res_model: "project.task",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "form"],
        ],
    });

    await contains(queryFirst(".o_data_cell")).click();
    const task1 = queryOne(".o_todo_done_button");
    expect(task1).not.toHaveClass("done_button_enabled", {
        message:
            "The checkmark on this task should be displayed as undone as its state is 01_in_progress",
    });
    task1.click();
    await animationFrame();
    expect(task1).toHaveClass("done_button_enabled", {
        message: "The checkmark on this task should be displayed as done as its state is 1_done",
    });
});

test("Check clicking on todo_done_checkmark in form view with initial state is done", async () => {
    onRpc("web_save", ({ args }) => {
        expect(args[1].state).toBe("01_in_progress", {
            message: "The task should be in progress",
        });
        expect.step("web_save");
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "To-do",
        res_model: "project.task",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "form"],
        ],
    });

    await contains(queryAll(".o_data_cell")[2]).click();
    const task2 = queryOne(".o_todo_done_button");
    expect(task2).toHaveClass("done_button_enabled", {
        message: "The checkmark on this task should be displayed as done as its state is 1_done",
    });
    task2.click();
    await animationFrame();
    expect(task2).not.toHaveClass("done_button_enabled", {
        message:
            "The checkmark on this task should be displayed as undone as its state is 01_in_progress",
    });
});
