/** @odoo-module */

import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";
import { userService } from "@web/core/user_service";
import { serializeDateTime } from "@web/core/l10n/dates";
import { click, editInput, getFixture, nextTick } from "@web/../tests/helpers/utils";

import { getPyEnv } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { setupTestEnv } from "@hr_timesheet/../tests/hr_timesheet_common_tests";
import { timerService } from "@timer/services/timer_service";
import { timesheetGridUOMService } from "@timesheet_grid/services/timesheet_grid_uom_service";

import { TimesheetGridSetupHelper } from "@timesheet_grid/../tests/helpers";

const { DateTime } = luxon;

let serverData, target, timesheetGridSetup;

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(async () => {
        timesheetGridSetup = new TimesheetGridSetupHelper(true);
        const result = await timesheetGridSetup.setupTimesheetGrid();
        serverData = result.serverData;
        let grid = serverData.views["analytic.line,false,grid"].replace(
            'js_class="timesheet_grid"',
            'js_class="timer_timesheet_grid"'
        );
        grid = grid.replace('widget="float_time"', 'widget="timesheet_uom"');
        serverData.views["analytic.line,false,grid"] = grid;
        grid = serverData.views["analytic.line,1,grid"].replace(
            'js_class="timesheet_grid"',
            'js_class="timer_timesheet_grid"'
        );
        grid = grid.replace('widget="float_time"', 'widget="timesheet_uom"');
        serverData.views["analytic.line,1,grid"] = grid;

        target = getFixture();
        setupTestEnv();
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("orm", ormService, { force: true });
        serviceRegistry.add("user", userService, { force: true });
        serviceRegistry.add("timer", timerService, { force: true });
        const gridComponentsRegistry = registry.category("grid_components");
        if (gridComponentsRegistry.contains("timesheet_uom")) {
            gridComponentsRegistry.remove("timesheet_uom"); // the component will be added by timesheet_grid_uom_service
        }
        serviceRegistry.add("timesheet_grid_uom", timesheetGridUOMService, { force: true });
    });

    QUnit.test("Timer already running with helpdesk ticket", async function (assert) {
        const pyEnv = getPyEnv();
        pyEnv.mockServer.models["analytic.line"].records.push({
            id: 10,
            unit_amount: 5740 / 3600, // 01:35:40
            project_id: 3,
            name: "Description",
        });
        let timerRunning = true;
        const { openView } = await start({
            serverData,
            async mockRPC(route, args) {
                if (args.method === "get_running_timer") {
                    const runningTimer = {
                        step_timer: 30,
                    };
                    if (timerRunning) {
                        return {
                            ...runningTimer,
                            id: 10,
                            project_id: 3,
                            start: 5740, // 01:35:40
                            description: "Description",
                        };
                    }
                    return runningTimer;
                } else if (args.method === "action_start_new_timesheet_timer") {
                    return false;
                } else if (args.method === "get_daily_working_hours") {
                    assert.strictEqual(args.model, "hr.employee");
                    return {};
                } else if (args.method === "get_server_time") {
                    assert.strictEqual(args.model, "timer.timer");
                    return serializeDateTime(DateTime.now());
                } else if (args.method === "action_timer_stop") {
                    timerRunning = false;
                    return null;
                }
                return timesheetGridSetup.mockTimesheetGridRPC(route, args);
            },
        });
        await openView({
            res_model: "analytic.line",
            views: [[false, "grid"]],
            context: { group_by: ["project_id", "helpdesk_ticket_id"] },
        });
        await nextTick();
        assert.containsNone(target, 'div[name="task_id"]');
        await editInput(
            target,
            "div[name='helpdesk_ticket_id'] .o_field_many2one_selection input",
            "fdfdfdf"
        );
        await click(target, ".btn_stop_timer");
    });
});
