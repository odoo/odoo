/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, editInput, getFixture } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

addModelNamesToFetch(["project.task"]);

let serverData;
let target;

QUnit.module("TodoEditableBreadcrumbName Tests", (hooks) => {
    hooks.beforeEach(async () => {
        const pyEnv = await startServer();
        pyEnv["project.task"].create([{ name: "Todo 1" }]); // To simulate a todo element
        serverData = {
            views: {
                "project.task,false,form": `<form js_class="todo_form"><field name="name"/></form>`,
                "project.task,false,list": `<tree><field name="name"/></tree>`,
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.test("Check changing TodoEditableBreadcrumbName input by a custom input in form view", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, { args, method }) {
                if (method === "web_save") {
                    assert.strictEqual(
                        args[1].name,
                        "Todo 42",
                        "The todo name should be updated"
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
        const breadcrumb_name_input = target.querySelector(".o_todo_breadcrumb_name_input");
        assert.hasClass(
            breadcrumb_name_input,
            "o_todo_breadcrumb_name_input",
            "The todo should have the appropriate class"
        );
        assert.strictEqual("Todo 1", breadcrumb_name_input.value);
        await editInput(target, ".o_todo_breadcrumb_name_input", "Todo 42");
        await click(breadcrumb_name_input);
        assert.doesNotHaveClass(
            breadcrumb_name_input,
            "o-todo-untitled",
            "The todo should not be untitled"
        );
        await click(target, ".o_form_button_save");
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("Check changing TodoEditableBreadcrumbName input by an empty input in form view", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, { args, method }) {
                if (method === "web_save") {
                    assert.strictEqual(
                        args[1].name,
                        "Untitled to-do",
                        "The todo name should be untitled"
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
        const breadcrumb_name_input = target.querySelector(".o_todo_breadcrumb_name_input");
        await editInput(target, ".o_todo_breadcrumb_name_input", "");
        await click(breadcrumb_name_input);
        assert.strictEqual(breadcrumb_name_input.placeholder, breadcrumb_name_input.value);
        assert.hasClass(
            breadcrumb_name_input,
            "o-todo-untitled",
            "The todo should be untitled"
        );
        await click(target, ".o_form_button_save");
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("Check changing TodoEditableBreadcrumbName input by the placeholder in form view", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, { args, method }) {
                if (method === "web_save") {
                    assert.strictEqual(
                        args[1].name,
                        "Untitled to-do",
                        "The todo name should be untitled"
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
        const breadcrumb_name_input = target.querySelector(".o_todo_breadcrumb_name_input");
        await editInput(
            target,
            ".o_todo_breadcrumb_name_input",
            breadcrumb_name_input.placeholder
        );
        await click(breadcrumb_name_input);
        assert.strictEqual(breadcrumb_name_input.placeholder, breadcrumb_name_input.value);
        assert.hasClass(
            breadcrumb_name_input,
            "o-todo-untitled",
            "The todo should be untitled"
        );
        await click(target, ".o_form_button_save");
        assert.verifySteps(["web_save"]);
    });
});
