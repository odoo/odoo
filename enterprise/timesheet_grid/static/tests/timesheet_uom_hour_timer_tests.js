/** @odoo-module */

import { serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";

import { makeView } from "@web/../tests/views/helpers";
import { click, getFixture } from "@web/../tests/helpers/utils";
import {
    getServerData,
    updateArch,
    setupTestEnv,
    addFieldsInArch,
} from "@hr_timesheet/../tests/hr_timesheet_common_tests";
import { timerService } from "@timer/services/timer_service";

const { DateTime } = luxon;


QUnit.module("timesheet_grid", (hooks) => {
    let target;
    let makeViewArgs;
    let now = DateTime.utc();
    const mockGetServerTimeRPC = function (route, { args, method }) {
        if (method === "get_server_time") {
            return Promise.resolve(serializeDateTime(now));
        }
    };
    hooks.beforeEach(async function (assert) {
        setupTestEnv();
        registry.category("services").add("orm", ormService, {force: true});
        registry.category("services").add("timer", timerService, { force: true });

        const serverData = getServerData();
        serverData.models["account.analytic.line"].fields.timer_start = { string: "Timer Started", type: 'datetime' };
        serverData.models["account.analytic.line"].fields.timer_pause = { string: "Timer Paused", type: 'datetime' };
        serverData.models["account.analytic.line"].fields.duration_unit_amount = { string: "Duration Unit Amount", type: 'float' };
        serverData.models["account.analytic.line"].fields.display_timer = { string: "Display Timer", type: 'boolean' };
        serverData.models["account.analytic.line"].fields.is_timer_running = { string: "Is Timer Running", type: 'boolean' };
        addFieldsInArch(serverData, ["timer_start", "timer_pause", "duration_unit_amount", "display_timer", "is_timer_running"], "unit_amount");
        updateArch(serverData, { unit_amount: "timesheet_uom_hour_timer" });
        for (let id = 4; id < 7; id++) {
            serverData.models["account.analytic.line"].records.push({ id, project_id: false, task_id: false, unit_amount: 1 });
        }
        const treeView = serverData.views["account.analytic.line,false,list"];
        serverData.views["account.analytic.line,false,list"] = treeView.replace(
            `name="unit_amount"`,
            `name="unit_amount" readonly="timer_start and not timer_pause"`
        );
        for (let index = 0; index < serverData.models["account.analytic.line"].records.length; index++) {
            const record = serverData.models["account.analytic.line"].records[index];
            record.display_timer = Boolean(index % 4);
            record.timer_start = index % 3 ? serializeDateTime(now.minus({ days: 1 })) : false;
            record.timer_pause = index % 2 && record.timer_start ? serializeDateTime(now.minus({ hours: 1 })) : false;
            record.duration_unit_amount = record.unit_amount;
            record.is_timer_running = record.timer_start && !record.timer_pause;
        }

        makeViewArgs = {
            type: "list",
            resModel: "account.analytic.line",
            serverData,
            mockRPC: (route, { args, method }) => mockGetServerTimeRPC(route, { args, method }),
        };
        target = getFixture();
    });

    QUnit.module("timesheet_uom_hour_timer");

    function _checkButtonVisibility(row, shouldBeVisible, assert) {
        if (shouldBeVisible) {
            assert.containsOnce(row, 'div[name="unit_amount"] button i', "button should be visible");
        } else {
            assert.containsNone(row, 'div[name="unit_amount"] button i', "button should not be visible");
        }
    }

    QUnit.test("button is displayed when display_timer is true", async function (assert) {
        await makeView(makeViewArgs);
        const secondRow = target.querySelector(".o_list_table .o_data_row:nth-of-type(2)");
        _checkButtonVisibility(secondRow, true, assert);
    });

    QUnit.test("button is not displayed when in edition", async function (assert) {
        await makeView(makeViewArgs);
        const secondRow = target.querySelector(".o_list_table .o_data_row:nth-of-type(2)");
        _checkButtonVisibility(secondRow, true, assert);
        await click(secondRow, 'div[name="unit_amount"]');
        _checkButtonVisibility(secondRow, false, assert);
    });

    QUnit.test("button is displayed when timer is running", async function (assert) {
        await makeView(makeViewArgs);
        const thirdRow = target.querySelector(".o_list_table .o_data_row:nth-of-type(3)");
        _checkButtonVisibility(thirdRow, true, assert);
        await click(thirdRow, 'div[name="unit_amount"]');
        _checkButtonVisibility(thirdRow, true, assert);
    });

    QUnit.test("button is not displayed when display_timer is false", async function (assert) {
        await makeView(makeViewArgs);
        const firstRow = target.querySelector(".o_list_table .o_data_row:first-of-type");
        _checkButtonVisibility(firstRow, false, assert);
    });

    QUnit.test("icon is corresponding to is_timer_running", async function (assert) {
        await makeView(makeViewArgs);
        const secondRow = target.querySelector('.o_list_table .o_data_row:nth-of-type(2) div[name="unit_amount"] button i');
        const thirdRow = target.querySelector('.o_list_table .o_data_row:nth-of-type(3) div[name="unit_amount"] button i');
        assert.hasClass(secondRow, "fa-play");
        assert.hasClass(thirdRow, "fa-stop");
    });

    QUnit.test("correct rpc calls are performed (click play)", async function (assert) {
        const mockRPC = function (route, { args, method }) {
            if (method === "action_timer_start") {
                assert.step("action_timer_start");
                return Promise.resolve(true);
            } else {
                return mockGetServerTimeRPC(...arguments);
            }
        };
        await makeView({ ...makeViewArgs, mockRPC });
        const secondRow = target.querySelector('.o_list_table .o_data_row:nth-of-type(2) div[name="unit_amount"] button i');
        assert.hasClass(secondRow, "fa-play");
        await click(secondRow.parentNode);
        assert.verifySteps(["action_timer_start"]);
    });

    QUnit.test("correct rpc calls are performed (click stop)", async function (assert) {
        const mockRPC = function (route, { args, method }) {
            if (method === "action_timer_stop") {
                assert.step("action_timer_stop");
                return Promise.resolve(true);
            } else {
                return mockGetServerTimeRPC(...arguments);
            }
        };
        await makeView({ ...makeViewArgs, mockRPC });
        const thirdRow = target.querySelector('.o_list_table .o_data_row:nth-of-type(3) div[name="unit_amount"] button i');
        assert.hasClass(thirdRow, "fa-stop");
        await click(thirdRow.parentNode);
        assert.verifySteps(["action_timer_stop"]);
    });

});
