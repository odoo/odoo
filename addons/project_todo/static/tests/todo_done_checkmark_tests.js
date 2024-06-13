/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, getFixture } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

addModelNamesToFetch(["project.task"]);

let serverData;
let target;

QUnit.module("TodoDoneCheckmark Tests", (hooks) => {
    hooks.beforeEach(async () => {
        const pyEnv = await startServer();
        pyEnv["project.task"].create([{ state: "01_in_progress" }]); // To simulate a first todo element
        pyEnv["project.task"].create([{ state: "1_done" }]); // To simulate a second todo element
        serverData = {
            views: {
                "project.task,false,kanban": `
                    <kanban>
                        <template>
                            <t t-name="kanban-box">
                                <div>
                                    <field name="state" widget="todo_done_checkmark"/>
                                </div>
                            </t>
                        </template>
                    </kanban>`,
                "project.task,false,list": `
                    <tree>
                        <field name="state" widget="todo_done_checkmark" nolabel="1"/>
                    </tree>`,
                "project.task,false,form": `
                    <form js_class="todo_form">
                        <field name="state"/>
                    </form>`,
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.test("Check clicking on todo_done_checkmark in kanban view with initial state is in progress", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, { args, method }) {
                if (method === "web_save") {
                    assert.strictEqual(
                        args[1].state,
                        "1_done",
                        "The task should be marked as done"
                    );
                    assert.step("web_save");
                }
            },
        });
        await openView({
            res_model: "project.task",
            views: [[false, "kanban"]],
        });
        const task1 = target.querySelector(".o_kanban_record:first-child .o_todo_done_button");
        assert.doesNotHaveClass(
            task1,
            "done_button_enabled",
            "The checkmark on this task should be displayed as undone as its state is 01_in_progress"
        );
        await click(task1);
        assert.hasClass(
            task1,
            "done_button_enabled",
            "The checkmark on this task should be displayed as done as its state is 1_done"
        );
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("Check clicking on todo_done_checkmark in kanban view with initial state is done", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, { args, method }) {
                if (method === "web_save") {
                    assert.strictEqual(
                        args[1].state,
                        "01_in_progress",
                        "The task should be in progress"
                    );
                    assert.step("web_save");
                }
            },
        });
        await openView({
            res_model: "project.task",
            views: [[false, "kanban"]],
        });
        const task2 = target.querySelector(".o_kanban_record:nth-child(2) .o_todo_done_button");
        assert.hasClass(
            task2,
            "done_button_enabled",
            "The checkmark on this task should be displayed as done as its state is 1_done"
        );
        await click(task2);
        assert.doesNotHaveClass(
            task2,
            "done_button_enabled",
            "The checkmark on this task should be displayed as undone as its state is 01_in_progress"
        );
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("Check clicking on todo_done_checkmark in list view with initial state is in progress", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, { args, method }) {
                if (method === "web_save") {
                    assert.strictEqual(
                        args[1].state,
                        "1_done",
                        "The task should be marked as done"
                    );
                    assert.step("web_save");
                }
            },
        });
        await openView({
            res_model: "project.task",
            views: [[false, "list"]],
        });
        const tasks = target.querySelector(".o_data_cell");
        const task1 = tasks.querySelector(".o_todo_done_button");
        assert.doesNotHaveClass(
            task1,
            "done_button_enabled",
            "The checkmark on this task should be displayed as undone as its state is 01_in_progress"
        );
        await click(task1);
        assert.hasClass(
            task1,
            "done_button_enabled",
            "The checkmark on this task should be displayed as done as its state is 1_done"
        );
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("Check clicking on todo_done_checkmark in list view with initial state is done", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, { args, method }) {
                if (method === "web_save") {
                    assert.strictEqual(
                        args[1].state,
                        "01_in_progress",
                        "The task should be in progress"
                    );
                    assert.step("web_save");
                }
            },
        });
        await openView({
            res_model: "project.task",
            views: [[false, "list"]],
        });
        const tasks = target.querySelectorAll(".o_data_cell");
        const task2 = tasks[1].querySelector(".o_todo_done_button");
        assert.hasClass(
            task2,
            "done_button_enabled",
            "The checkmark on this task should be displayed as done as its state is 1_done"
        );
        await click(task2);
        assert.doesNotHaveClass(
            task2,
            "done_button_enabled",
            "The checkmark on this task should be displayed as undone as its state is 01_in_progress"
        );
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("Check clicking on todo_done_checkmark in form view with initial state is in progress", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, { args, method }) {
                if (method === "web_save") {
                    assert.strictEqual(
                        args[1].state,
                        "1_done",
                        "The task should be marked as done"
                    );
                    assert.step("web_save");
                }
            },
        });
        await openView({
            res_model: "project.task",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        });
        await click(target.querySelector(".o_data_cell"));
        const task1 = target.querySelector(".o_todo_done_button");
        assert.doesNotHaveClass(
            task1,
            "done_button_enabled",
            "The checkmark on this task should be displayed as undone as its state is 01_in_progress"
        );
        await click(task1);
        assert.hasClass(
            task1,
            "done_button_enabled",
            "The checkmark on this task should be displayed as done as its state is 1_done"
        );
        await click(target, ".o_form_button_save");
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("Check clicking on todo_done_checkmark in form view with initial state is done", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, { args, method }) {
                if (method === "web_save") {
                    assert.strictEqual(
                        args[1].state,
                        "01_in_progress",
                        "The task should be in progress"
                    );
                    assert.step("web_save");
                }
            },
        });
        await openView({
            res_model: "project.task",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        });
        await click(target.querySelectorAll(".o_data_cell")[1]);
        const task2 = target.querySelector(".o_todo_done_button");
        assert.hasClass(
            task2,
            "done_button_enabled",
            "The checkmark on this task should be displayed as done as its state is 1_done"
        );
        await click(task2);
        assert.doesNotHaveClass(
            task2,
            "done_button_enabled",
            "The checkmark on this task should be displayed as undone as its state is 01_in_progress"
        );
        await click(target, ".o_form_button_save");
        assert.verifySteps(["web_save"]);
    });
});
