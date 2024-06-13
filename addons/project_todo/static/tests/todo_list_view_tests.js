/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, getFixture } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

addModelNamesToFetch(["project.task"]);

let serverData;
let target;

QUnit.module("todoListView Tests", (hooks) => {
    hooks.beforeEach(async () => {
        const pyEnv = await startServer();
        pyEnv["project.task"].create([{}]); // To simulate a todo element
        serverData = {
            views: {
                "project.task,false,list": `<tree js_class="todo_list"></tree>`,
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.test("Check that todo_list view is restricted to archive, unarchive, duplicate and delete menu actions", async function (assert) {
        assert.expect(1);
        const { openView } = await start({
            serverData,
        });
        await openView({
            res_model: "project.task",
            views: [[false, "list"]],
        });
        await click(target.querySelector(".o_list_record_selector input"));
        await click(target.querySelector(".o_cp_action_menus button"));
        let menuActions = Array.from(target.querySelectorAll(".o_menu_item"));
        menuActions = menuActions.map((menuAction) => menuAction.innerText);
        const actionsToKeep = ["Export", "Archive", "Unarchive", "Duplicate", "Delete"];
        assert.deepEqual(menuActions, actionsToKeep);
    });
});
