/** @odoo-module **/

import { timesheetListSetupHelper } from "./helpers";

import { registry } from "@web/core/registry";
import { getFixture } from "@web/../tests/helpers/utils";
import { makeView } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("timesheet_grid", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                foo: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                    },
                    records: [
                        { id: 1, foo: "yop" },
                        { id: 2, foo: "bip" },
                    ]
                },
            },
        };
        timesheetListSetupHelper.setupTimesheetList();
        registry.category("services").add("create_edit_project_ids", {
            // fake service
            start() {
                return {
                    fetchProjectIds() {
                        return [];
                    },
                    get projectIds() {
                        return [];
                    },
                };
            },
        });
        target = getFixture();
    });

    QUnit.module("TimesheetTimerListView");

    QUnit.test("basic rendering", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<list js_class="timesheet_timer_list"><field name="foo"/></list>',
            async mockRPC(route, args) {
                if (args.method === "get_running_timer") {
                    return {
                        step_timer: 30,
                    };
                } else if (args.method === "get_timesheet_ranking_data") {
                    return {
                        "leaderboard": [],
                        "employee_id": false,
                        "total_time_target": false,
                    };
                }
            },
        });

        assert.containsOnce(target, ".o_timesheet_timer_list_view");
        assert.containsOnce(target, ".pinned_header .timesheet-timer");
        assert.containsOnce(target, ".o_pager");
        assert.strictEqual(target.querySelector(".o_pager").innerText, "1-2 / 2");
    });
});
