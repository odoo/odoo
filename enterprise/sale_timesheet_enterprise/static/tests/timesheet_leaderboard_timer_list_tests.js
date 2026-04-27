import { timesheetListSetupHelper } from "@timesheet_grid/../tests/helpers";

import { registry } from "@web/core/registry";
import { getFixture } from "@web/../tests/helpers/utils";
import { makeView } from "@web/../tests/views/helpers";

let target;

async function initAndOpenView(showIndicators = true, showLeaderboard = true) {
    await makeView({
        type: "list",
        resModel: "foo",
        serverData: {
            models: {
                foo: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                    },
                },
            },
        },
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
            } else if (args.method === "read" && args.args[1].length === 2 && args.args[1][0] === "timesheet_show_rates" && args.args[1][1] === "timesheet_show_leaderboard") {
                return [{ timesheet_show_rates: showIndicators, timesheet_show_leaderboard: showLeaderboard }];
            }
        },
    });
}

QUnit.module("Timesheet Leaderboard List View", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
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
    });

    QUnit.test("Check that leaderboard is displayed if user's company has the features on.", async function (assert) {
        await initAndOpenView();
        assert.containsOnce(target, ".o_timesheet_leaderboard");
    });

    QUnit.test("Check that leaderboard is not displayed if user's company doesn't have the features on.", async function (assert) {
        await initAndOpenView(false, false);
        assert.containsNone(target, ".o_timesheet_leaderboard");
    });
});
