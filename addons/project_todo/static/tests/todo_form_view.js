/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, getFixture } from "@web/../tests/helpers/utils";
import { contains } from "@web/../tests/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

import { patchUserWithCleanup } from "@web/../tests/helpers/mock_services";

addModelNamesToFetch(["project.task"]);

let serverData;
let target;

QUnit.module("todoFormView Tests", (hooks) => {
    hooks.beforeEach(async () => {
        const pyEnv = await startServer();
        pyEnv["project.task"].create([{ name: "Todo 1", state: "01_in_progress" }]); // To simulate a todo element
        serverData = {
            views: {
                "project.task,false,form": `
                    <form js_class="todo_form">
                        <field name="name"/>
                        <field name="state"/>
                    </form>`,
                "project.task,false,list": `
                    <tree>
                        <field name="name"/>
                        <field name="state"/>
                    </tree>`,
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.test("Check that project_task_action_convert_todo_to_task appears in the menu actions if the user does belong to the group_project_user group", async function (assert) {
        assert.expect(1);
        const { openView } = await start({
            serverData,
        });
        await openView({
            res_model: "project.task",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        });
        patchUserWithCleanup({ hasGroup: async (group) => group === "project.group_project_user" });  // For the user to have access to project_task_action_convert_todo_to_task
        await click(target.querySelector(".o_data_cell"));
        await click(target.querySelector(".o_cp_action_menus button"));
        let menuActions = Array.from(target.querySelectorAll(".o-dropdown--menu span"));
        menuActions = menuActions.map((menuAction) => menuAction.innerText);
        assert.ok(
            menuActions.includes("Convert to Task"),
            "project_task_action_convert_todo_to_task action should appear in the menu actions"
        );
    });

    QUnit.test("Check that project_task_action_convert_todo_to_task does not appear in the menu actions if the user does not belong to the group_project_user group", async function (assert) {
        assert.expect(1);
        const { openView } = await start({
            serverData,
        });
        await openView({
            res_model: "project.task",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        });
        await click(target.querySelector(".o_data_cell"));
        await click(target.querySelector(".o_cp_action_menus button"));
        let menuActions = Array.from(target.querySelectorAll(".o-dropdown--menu span"));
        menuActions = menuActions.map((menuAction) => menuAction.innerText);
        assert.notOk(
            menuActions.includes("Convert to Task"),
            "project_task_action_convert_todo_to_task action should not appear in the menu actions"
        );
    });

    QUnit.test("Check that todo_form view contains the TodoDoneCheckmark and TodoEditableBreadcrumbName widgets", async function (assert) {
        assert.expect(2);
        const { openView } = await start({
            serverData,
        });
        await openView({
            res_model: "project.task",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        });
        await click(target.querySelector(".o_data_cell"));
        await contains(".o_todo_breadcrumb_name_input");
        await contains(".o_todo_done_button");
    });
});
