/** @odoo-module */

import { makeView } from "@web/../tests/views/helpers";
import { click, clickDropdown, editInput, getFixture } from "@web/../tests/helpers/utils";

import { getServerData, updateArch, setupTestEnv } from "./hr_timesheet_common_tests";


QUnit.module("hr_timesheet", (hooks) => {
    let target;
    let serverData;
    hooks.beforeEach(async function (assert) {
        setupTestEnv();
        serverData = getServerData();
        updateArch(
            serverData,
            { task_id: "task_with_hours" },
            { task_id: "{ 'default_project_id': project_id }" });
        target = getFixture();
    });

    QUnit.module("task_with_hours");

    async function _testCreateAndEdit(target, visible, assert) {
        await click(target, ".o_list_many2one[name=task_id]");
        await click(target, ".o_list_many2one[name=task_id] input");
        await editInput(target, ".o_list_many2one[name=task_id] input", "NonExistingTask");
        await click(target, ".o_list_many2one[name=task_id] input");
        await clickDropdown(target, "task_id");
        const testFunction = visible ? assert.containsOnce : assert.containsNone;
        testFunction(target, '.o_list_many2one[name=task_id] .dropdown ul li:contains(Create "NonExistingTask")');
    }

    QUnit.test("quick create is enabled when project_id is set", async function (assert) {
        await makeView({
            serverData,
            type: "list",
            resModel: "account.analytic.line",
        });
        const secondRow = target.querySelector(".o_list_table .o_data_row:nth-of-type(2)");
        await _testCreateAndEdit(secondRow, true, assert);
    });

    QUnit.test("quick create is no enabled when project_id is not set", async function (assert) {
        await makeView({
            serverData,
            type: "list",
            resModel: "account.analytic.line",
        });
        const thirdRow = target.querySelector(".o_list_table .o_data_row:nth-of-type(3)");
        await _testCreateAndEdit(thirdRow, false, assert);
    });

    QUnit.test("the text of the task includes hours in the drop down but not in the line", async function (assert) {
        await makeView({
            serverData,
            type: "list",
            resModel: "account.analytic.line",
        });
        const firstRow = target.querySelector(".o_list_table .o_data_row:first-of-type");
        assert.containsNone(firstRow, '.o_list_many2one[name=task_id]:contains("AdditionalInfo")');
        await click(firstRow, ".o_list_many2one[name=task_id]");
        await clickDropdown(firstRow, "task_id");
        assert.containsN(firstRow, '.o_list_many2one[name=task_id] .dropdown ul li:contains("AdditionalInfo")', 3);
    });

});
