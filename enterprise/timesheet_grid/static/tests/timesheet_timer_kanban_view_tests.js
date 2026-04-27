
/** @odoo-module */

import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";
import { serializeDateTime } from "@web/core/l10n/dates";
import {
    click,
    clickOpenM2ODropdown,
    editInput,
    getFixture,
    nextTick,
} from "@web/../tests/helpers/utils";

import { getPyEnv } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { setupTestEnv } from "@hr_timesheet/../tests/hr_timesheet_common_tests";
import { timesheetGridUOMService } from "@timesheet_grid/services/timesheet_grid_uom_service";

import { TimesheetGridSetupHelper } from "./helpers";

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
        const gridComponentsRegistry = registry.category("grid_components");
        if (gridComponentsRegistry.contains("timesheet_uom")) {
            gridComponentsRegistry.remove("timesheet_uom"); // the component will be added by timesheet_grid_uom_service
        }
        serviceRegistry.add("timesheet_grid_uom", timesheetGridUOMService, { force: true });
    });

    QUnit.module("TimesheetTimerKanbanView");

    QUnit.test("Switch view with GroupBy and start the timer", async function (assert) {
        serverData.views["analytic.line,1,kanban"] =
            `<kanban js_class="timesheet_timer_kanban">
                <templates>
                    <field name="name"/>
                    <t t-name="card">
                        <field name="employee_id"/>
                        <field name="project_id"/>
                        <field name="task_id"/>
                        <field name="date"/>
                        <field name="display_timer"/>
                        <field name="unit_amount"/>
                    </t>
                </templates>
            </kanban>`;

        const pyEnv = getPyEnv();
        const { openView } = await start({
            serverData,
            async mockRPC(route, { method }) {
                switch (method) {
                    case "get_running_timer":
                        return { step_timer: 30 };
                    case "action_start_new_timesheet_timer":
                        const newTimesheet = {
                            id: 7,
                            project_id: 1,
                            task_id: false,
                            date: serializeDateTime(DateTime.now()),
                            unit_amount: 0.0,
                        };
                        pyEnv.mockServer.models["analytic.line"].records.push(newTimesheet);
                        return newTimesheet;
                    case "get_daily_working_hours":
                        return {};
                    case "get_server_time":
                        return serializeDateTime(DateTime.now());
                    case "get_create_edit_project_ids":
                        return [];
                    default:
                        return timesheetGridSetup.mockTimesheetGridRPC(...arguments);
                }
            }
        });

        await openView({
            res_model: "analytic.line",
            views: [[false, "grid"], [false, "kanban"]],
            context: { group_by: ["project_id", "task_id"] },
        });
        await nextTick();
        await click(target, ".o_switch_view.o_kanban");
        await nextTick();
        await click(target, ".btn_start_timer");
        assert.containsNone(
            target,
            "button.btn_start_timer",
            "Timer should be running"
        );
    });

    QUnit.test("Start timer, set fields and switch view", async function (assert) {
        const pyEnv = getPyEnv();
        const timesheetModel = pyEnv.mockServer.models["analytic.line"];
        timesheetModel.fields.is_timer_running = { string: "Running Timer", type: "boolean" };

        let timerRunning = false;
        serverData.views["analytic.line,1,kanban"] =
            `<kanban js_class="timesheet_timer_kanban">
                <templates>
                    <field name="name"/>
                    <t t-name="card">
                        <field name="employee_id"/>
                        <field name="project_id"/>
                        <field name="task_id"/>
                        <field name="date"/>
                        <field name="is_timer_running"/>
                        <field name="display_timer"/>
                        <field name="unit_amount"/>
                    </t>
                </templates>
            </kanban>`;

        const { openView } = await start({
            serverData,
            async mockRPC(route, { method }) {
                switch (method) {
                    case "get_running_timer":
                        const result = { step_timer: 30 };
                        if (timerRunning) {
                            result.id = 4;
                        }
                        return result;
                    case "action_start_new_timesheet_timer":
                        timerRunning = true;
                        pyEnv.mockServer.models["analytic.line"].records[3].is_timer_running = true;
                        return { id: 4 };
                    case "get_daily_working_hours":
                        return {};
                    case "get_server_time":
                        return serializeDateTime(DateTime.now());
                    case "get_create_edit_project_ids":
                        return [];
                    default:
                        return timesheetGridSetup.mockTimesheetGridRPC(...arguments);
                }
            }
        });

        await openView({
            res_model: "analytic.line",
            views: [[false, "kanban"], [false, "grid"]],
        });
        await nextTick();
        await click(target, ".btn_start_timer");
        await editInput(target, ".o_field_char[name='name'] input", "Test");
        await clickOpenM2ODropdown(target, "task_id");
        await click(target, ".o_field_many2one[name='task_id'] li:nth-of-type(1) a");
        await click(target, ".o_switch_view.o_grid");
        assert.equal(
            target.querySelector(".o_field_char[name='name'] input").value,
            "Test",
            "Description shouldn't have changed by switching view"
        );
        assert.equal(
            target.querySelector(".o_field_many2one[name='task_id'] input").value,
            "BS task",
            "Task shouldn't have changed by switching view"
        );
    });

    QUnit.test("Unlink timesheet through timesheet_uom_timer widget", async function (assert) {
        const pyEnv = getPyEnv();
        const timesheetModel = pyEnv.mockServer.models["analytic.line"];
        timesheetModel.fields.is_timer_running = { string: "Running Timer", type: "boolean" };
        timesheetModel.records[0].is_timer_running = true;

        serverData.views["analytic.line,1,kanban"] = `
            <kanban js_class="timesheet_timer_kanban">
                <templates>
                    <field name="name"/>
                    <t t-name="card">
                        <field name="employee_id"/>
                        <field name="project_id"/>
                        <field name="task_id"/>
                        <field name="date"/>
                        <field name="is_timer_running"/>
                        <field name="display_timer"/>
                        <field name="unit_amount" widget="timesheet_uom_timer"/>
                    </t>
                </templates>
            </kanban>`;

        const { openView } = await start({
            serverData,
            async mockRPC(route, { method }) {
                switch (method) {
                    case "action_timer_stop":
                        return Promise.resolve(true);
                    case "get_running_timer":
                        return {
                            id: 1,
                            start: 5740, // 01:35:40
                            step_timer: 30,
                        };
                    case "action_start_new_timesheet_timer":
                        return true;
                    case "get_server_time":
                        return serializeDateTime(DateTime.now());
                    case "get_create_edit_project_ids":
                        return [];
                }
            }
        });

        await openView({
            res_model: "analytic.line",
            views: [[false, "kanban"]],
            context: { group_by: ["project_id", "task_id"], my_timesheet_display_timer: 1 },
        });

        await nextTick();
        // Verify the stop button is displayed in the kanban view.
        assert.strictEqual(target.querySelector(".o_icon_button").title, 'Stop', "The timer stop button should be visible");

        // Stop the timer using the kanban view (timesheet_uom_timer widget).
        await click(target, ".o_icon_button");
        await nextTick();

        // Verify that the project input is removed after stopping the timer.
        assert.strictEqual(target.querySelector('div[name="project_id"] input'), null, "The project input should not exist");
    });

    QUnit.test("Timer should not start when adding new record", async function (assert) {
        let timerStarted = false;
        serverData.views = {
            "analytic.line,false,kanban":
                `<kanban js_class="timesheet_timer_kanban">
                    <templates>
                        <field name="name"/>
                        <t t-name="card">
                            <field name="employee_id"/>
                            <field name="project_id"/>
                            <field name="task_id"/>
                            <field name="date"/>
                            <field name="display_timer"/>
                            <field name="unit_amount"/>
                        </t>
                    </templates>
                </kanban>`,
            "analytic.line,false,list":
                `<list js_class="timesheet_timer_list" editable="bottom">
                    <field name="project_id"/>
                </list>`,
            "analytic.line,false,search":
                `<search>
                    <field name="project_id"/>
                </search>`,
        }

        const { openView } = await start({
            serverData,
            async mockRPC(route, { method }) {
                switch (method) {
                    case "get_running_timer":
                        const result = { step_timer: 30 };
                        return result;
                    case "action_start_new_timesheet_timer":
                        timerStarted = true;
                        return false;
                    case "get_daily_working_hours":
                        return {};
                    case "get_server_time":
                        return serializeDateTime(DateTime.now());
                    case "get_create_edit_project_ids":
                        return [];
                    default:
                        return timesheetGridSetup.mockTimesheetGridRPC(...arguments);
                }
            }
        });

        await openView({
            res_model: "analytic.line",
            views: [[false, "list"], [false, "kanban"]],
        });
        await nextTick();
        await click(target, ".o_list_button_add");
        await click(target.querySelector(".o-autocomplete--input"));
        await click(target.querySelector(".o-autocomplete .o-autocomplete--dropdown-item"));
        await click(target, ".o_switch_view.o_kanban");
        assert.containsOnce(
            target,
            ".btn_start_timer",
            "Timer should not have started"
        );
        assert.strictEqual(timerStarted, false, "action_start_new_timesheet_timer should not be called");
    });
})
