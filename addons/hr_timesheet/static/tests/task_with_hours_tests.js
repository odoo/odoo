/** @odoo-module */

import { registry } from "@web/core/registry";
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
        registry.category("services").add("create_edit_project_ids", {
            start() {
                return {};
            },
        });
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
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/project.project/get_create_edit_project_ids') {
                    return [];
                }
            },
            type: "list",
            resModel: "account.analytic.line",
        });
        const secondRow = target.querySelector(".o_list_table .o_data_row:nth-of-type(2)");
        await _testCreateAndEdit(secondRow, true, assert);
    });

    QUnit.test("quick create is no enabled when project_id is not set", async function (assert) {
        await makeView({
            serverData,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/project.project/get_create_edit_project_ids') {
                    return [];
                }
            },
            type: "list",
            resModel: "account.analytic.line",
        });
        const thirdRow = target.querySelector(".o_list_table .o_data_row:nth-of-type(3)");
        await _testCreateAndEdit(thirdRow, false, assert);
    });

    QUnit.test("the text of the task includes hours in the drop down but not in the line", async function (assert) {
        await makeView({
            serverData,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/project.project/get_create_edit_project_ids') {
                    return [];
                }
            },
            type: "list",
            resModel: "account.analytic.line",
        });
        const firstRow = target.querySelector(".o_list_table .o_data_row:first-of-type");
        assert.containsNone(firstRow, '.o_list_many2one[name=task_id]:contains("AdditionalInfo")');
        await click(firstRow, ".o_list_many2one[name=task_id]");
        await clickDropdown(firstRow, "task_id");
        assert.containsN(firstRow, '.o_list_many2one[name=task_id] .dropdown ul li:contains("AdditionalInfo")', 3);
    });

    QUnit.test("project task progress bar color", async function (assert) {
        await makeView({
            serverData,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/project.project/get_create_edit_project_ids') {
                    return [];
                }
            },
            type: "list",
            resModel: "project.task",
            arch: `
                <list>
                    <field name="name"/>
                    <field name="project_id"/>
                    <field name="progress" widget="project_task_progressbar" options="{'overflow_class': 'bg-danger'}"/>
                </list>
            `,
        });

        assert.containsOnce(target, "div.o_progressbar .bg-success", "Task 1 having progress = 50 < 80 => green color")
        assert.containsOnce(target, "div.o_progressbar .bg-warning", "Task 2 having progress = 80 >= 80 => orange color")
        assert.containsOnce(target, "div.o_progressbar .bg-success", "Task 3 having progress = 101 > 100 => red color")
    });
});
