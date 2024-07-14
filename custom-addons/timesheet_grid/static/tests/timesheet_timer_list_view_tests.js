/** @odoo-module **/

import { timesheetListSetupHelper } from "./helpers";

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
        target = getFixture();
    });

    QUnit.module("TimesheetTimerListView");

    QUnit.test("basic rendering", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree js_class="timesheet_timer_list"><field name="foo"/></tree>',
            context: { my_timesheet_display_timer: 1 },
            async mockRPC(route, args) {
                if (args.method === "get_running_timer") {
                    return {
                        step_timer: 30,
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
