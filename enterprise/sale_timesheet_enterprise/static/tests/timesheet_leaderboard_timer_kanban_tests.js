import { timesheetListSetupHelper } from "@timesheet_grid/../tests/helpers";

import { getFixture } from "@web/../tests/helpers/utils";
import { makeView } from "@web/../tests/views/helpers";

let target;

async function initAndOpenView(showIndicators = true, showLeaderboard = true) {
    await makeView({
        type: "kanban",
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
        arch:
            `<kanban js_class="timesheet_timer_kanban">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
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

QUnit.module("Timesheet Leaderboard Kanban View", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        timesheetListSetupHelper.setupTimesheetList(); // all this does is add the helpdesk service when helpdesk is installed, so we can use it for kanban too
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
