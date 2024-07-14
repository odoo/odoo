/** @odoo-module */

import { session } from "@web/session";

import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";
import { serializeDateTime } from "@web/core/l10n/dates";
import {
    patchWithCleanup,
    triggerEvent,
    getFixture,
    click,
    nextTick,
} from "@web/../tests/helpers/utils";
import { start } from "@mail/../tests/helpers/test_utils";

import { setupTestEnv } from "@hr_timesheet/../tests/hr_timesheet_common_tests";
import { timerService } from "@timer/services/timer_service";
import { timesheetGridUOMService } from "@timesheet_grid/services/timesheet_grid_uom_service";

import { TimesheetGridSetupHelper } from "./helpers";
import { hoverGridCell } from "@web_grid/../tests/helpers";

const { DateTime } = luxon;

let serverData, target, timesheetGridSetup;

QUnit.module("timesheet_grid", function (hooks) {
    hooks.beforeEach(async () => {
        timesheetGridSetup = new TimesheetGridSetupHelper(true);
        const result = await timesheetGridSetup.setupTimesheetGrid();
        const pyEnv = result.pyEnv;
        const timesheetModel = pyEnv.mockServer.models["analytic.line"];
        timesheetModel.fields.timer_start = {
            string: "Timer Start",
            type: "datetime",
        };
        timesheetModel.fields.company_id = {
            type: "many2one",
            relation: "res.company",
        };
        serverData = result.serverData;
        let grid = serverData.views["analytic.line,false,grid"].replace(
            'widget="float_time"',
            'widget="timesheet_uom"'
        );
        grid = grid.replace('widget="float_time"', 'widget="timesheet_uom"');
        serverData.views["analytic.line,false,grid"] = grid;

        grid = serverData.views["analytic.line,1,grid"].replace(
            'widget="float_time"',
            'widget="timesheet_uom"'
        );
        serverData.views["analytic.line,1,grid"] = grid;

        setupTestEnv();
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("orm", ormService, { force: true });
        serviceRegistry.add("timer", timerService, { force: true });
        const gridComponentsRegistry = registry.category("grid_components");
        if (gridComponentsRegistry.contains("timesheet_uom")) {
            gridComponentsRegistry.remove("timesheet_uom"); // the component will be added by timesheet_grid_uom_service
        }
        serviceRegistry.add("timesheet_grid_uom", timesheetGridUOMService, { force: true });
        target = getFixture();
    });

    QUnit.module("timesheet_uom in grid_components registry");

    QUnit.test(
        "the timesheet_uom widget added to the WebGrid fieldRegistry is company related",
        async function (assert) {
            const { openView } = await start({
                serverData,
                async mockRPC(route, args) {
                    if (args.method === "get_running_timer") {
                        return {
                            step_timer: 30,
                        };
                    } else if (args.method === "action_start_new_timesheet_timer") {
                        return false;
                    } else if (args.method === "get_daily_working_hours") {
                        assert.strictEqual(args.model, "hr.employee");
                        return {};
                    }
                    return timesheetGridSetup.mockTimesheetGridRPC(route, args);
                },
            });

            await openView({
                res_model: "analytic.line",
                views: [[false, "grid"]],
                context: { group_by: ["task_id", "project_id"] },
            });

            const cell = target.querySelector(
                ".o_grid_row:not(.o_grid_row_total,.o_grid_row_title,.o_grid_column_total)"
            );
            assert.strictEqual(cell.textContent, "0:00", "float_time formatter should be used");
            await triggerEvent(cell, null, "mouseover");
            assert.strictEqual(cell.textContent, "0:00", "float_time formatter should be used");
        }
    );

    QUnit.test(
        "timesheet_uom widget should be float_toggle if uom is days",
        async function (assert) {
            patchWithCleanup(session.user_companies.allowed_companies[1], { timesheet_uom_id: 2 });
            const { openView } = await start({
                serverData,
                async mockRPC(route, args) {
                    if (args.method === "get_running_timer") {
                        return {
                            step_timer: 30,
                        };
                    } else if (args.method === "action_start_new_timesheet_timer") {
                        return false;
                    } else if (args.method === "get_daily_working_hours") {
                        assert.strictEqual(args.model, "hr.employee");
                        return {};
                    } else if (args.method === "get_server_time") {
                        assert.strictEqual(args.model, "timer.timer");
                        return serializeDateTime(DateTime.now());
                    } else if (args.method === "action_timer_unlink") {
                        return null;
                    }
                    return timesheetGridSetup.mockTimesheetGridRPC(route, args);
                },
            });
            await openView({
                res_model: "analytic.line",
                views: [[false, "grid"]],
                context: { group_by: ["task_id", "project_id"] },
            });
            const cell = target.querySelector(
                ".o_grid_row:not(.o_grid_row_total,.o_grid_row_title,.o_grid_column_total)"
            );
            assert.strictEqual(cell.textContent, "0.00", "float_toggle formatter should be used");
            await triggerEvent(cell, null, "mouseover");
            assert.strictEqual(cell.textContent, "0.00", "float_toggle formatter should be used");
        }
    );
    QUnit.test(
        "timesheet_uom widget should be float_factor if uom is foo",
        async function (assert) {
            patchWithCleanup(session.user_companies.allowed_companies[1], { timesheet_uom_id: 3 });
            const { openView } = await start({
                serverData,
                async mockRPC(route, args) {
                    if (args.method === "get_running_timer") {
                        return {
                            step_timer: 30,
                        };
                    } else if (args.method === "action_start_new_timesheet_timer") {
                        return false;
                    } else if (args.method === "get_daily_working_hours") {
                        assert.strictEqual(args.model, "hr.employee");
                        return {};
                    } else if (args.method === "get_server_time") {
                        assert.strictEqual(args.model, "timer.timer");
                        return serializeDateTime(DateTime.now());
                    } else if (args.method === "action_timer_unlink") {
                        return null;
                    }
                    return timesheetGridSetup.mockTimesheetGridRPC(route, args);
                },
            });
            await openView({
                res_model: "analytic.line",
                views: [[false, "grid"]],
                context: { group_by: ["task_id", "project_id"] },
            });
            const cell = target.querySelector(
                ".o_grid_row:not(.o_grid_row_total,.o_grid_row_title,.o_grid_column_total)"
            );
            assert.strictEqual(cell.textContent, "0.00", "float_factor formatter should be used");
            await triggerEvent(cell, null, "mouseover");
            assert.strictEqual(cell.textContent, "0.00", "float_factor formatter should be used");
        }
    );

    QUnit.test("Clicking on the magnifying glass doesn't toggle the cell", async function (assert) {
        patchWithCleanup(session.user_companies.allowed_companies[1], { timesheet_uom_id: 2 });
        const { openView } = await start({
            serverData,
            async mockRPC(route, args) {
                if (args.method === "get_running_timer") {
                    return {
                        step_timer: 30,
                    };
                } else if (args.method === "action_start_new_timesheet_timer") {
                    return false;
                } else if (args.method === "get_daily_working_hours") {
                    assert.strictEqual(args.model, "hr.employee");
                    return {};
                } else if (args.method === "get_server_time") {
                    assert.strictEqual(args.model, "timer.timer");
                    return serializeDateTime(DateTime.now());
                } else if (args.method === "action_timer_unlink") {
                    return null;
                }
                return timesheetGridSetup.mockTimesheetGridRPC(route, args);
            },
        });
        await openView({
            res_model: "analytic.line",
            views: [[false, "grid"]],
            context: { group_by: ["task_id", "project_id"] },
        });
        const cell = target.querySelector(
            ".o_grid_row:not(.o_grid_row_total,.o_grid_row_title,.o_grid_column_total)"
        );
        assert.strictEqual(cell.textContent, "0.00", "Initial cell content should be 0.00");
        await hoverGridCell(cell);
        await nextTick();
        await click(target, ".o_grid_search_btn");
        assert.strictEqual(
            cell.textContent,
            "0.00",
            "Clicking on the magnifying glass shouldn't alter the content of the cell"
        );
    });
});
