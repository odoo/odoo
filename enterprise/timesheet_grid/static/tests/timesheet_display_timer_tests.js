/** @odoo-module */

import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";
import { serializeDateTime } from "@web/core/l10n/dates";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture, mount, nextTick } from "@web/../tests/helpers/utils";

import { TimesheetDisplayTimer, TimesheetTimerFloatTimerField } from "@timesheet_grid/components/timesheet_display_timer/timesheet_display_timer";
import { EventBus } from "@odoo/owl";
import { timerService } from "@timer/services/timer_service";

const { DateTime } = luxon;


QUnit.module("timesheet_grid", (hooks) => {
    let target;
    let now;
    hooks.beforeEach(async function (assert) {
        target = getFixture();
        now = DateTime.utc();
        registry.category("services").add("orm", ormService, {force: true});
        registry.category("services").add("timer", timerService, { force: true });
    });

    QUnit.module("TimesheetTimerFloatTimerField");

    async function _testTimesheetTimerFloatTimerField(timerRunning, assert) {
        const env = await makeTestEnv();
        const props = {
            value: 12 + 34 / 60 + (timerRunning ? 56 / 3600 : 0),
            timerRunning,
            record: {
                isInvalid: () => false,
                model: { bus: new EventBus() },
                isFieldInvalid: () => {},
            },
            displayRed: false,
        };
        await mount(TimesheetTimerFloatTimerField, target, { env, props });
        await nextTick();
        const inputText = target.querySelector("input.o_input").value;
        assert.equal(`12:34${timerRunning ? ":56" : ""}`, inputText, `TimesheetTimerFloatTimerField should ${!timerRunning ? "not " : ""}display seconds when 'timerRunning' is ${timerRunning ? "true" : "false"}.`);
    }

    QUnit.test("TimesheetTimerFloatTimerField displays seconds when timerRunning is true", async function (assert) {
        await _testTimesheetTimerFloatTimerField(true, assert);
    });

    QUnit.test("TimesheetTimerFloatTimerField does not displays seconds when timerRunning is false", async function (assert){
        await _testTimesheetTimerFloatTimerField(false, assert);
    });

    QUnit.module("TimesheetDisplayTimer");

    async function _testTimesheetDisplayTimer(duration, timerStart, timerPause, expectedRunning, assert) {
        const env = await makeTestEnv({
            mockRPC(route, { args, method }) {
                if (method === "get_server_time") {
                    return Promise.resolve(serializeDateTime(now));
                }
            },
        });
        const props = {
            name: "plop",
            record: {
                resModel: "dummy",
                isInvalid: () => false,
                model: { bus: new EventBus() },
                data: {
                    timer_start: timerStart,
                    timer_pause: timerPause,
                    plop: duration,
                },
                isFieldInvalid: () => {},
            },
        };
        await mount(TimesheetDisplayTimer, target, { env, props: props });
        await nextTick();
        const timerStartInput = target.querySelector("input");
        const originalValue = timerStartInput.value;
        await new Promise(resolve => setTimeout(resolve, 2000));
        const currentValue = timerStartInput.value;
        if (expectedRunning) {
          assert.notEqual(originalValue, currentValue, `value should have been updated after 1 second interval`);
        } else {
          assert.equal(originalValue, currentValue, `value should not have been updated after 1 second interval`);
        }
    }

    QUnit.test("timesheet_display_timer updates the timer when timer_start is not falsy and when timer_pause is falsy", async function (assert) {
        await _testTimesheetDisplayTimer(1, now.minus({ hours: 1 }), false, true, assert);
    });

    QUnit.test("timesheet_display_timer does not update the timer when timer_start is falsy", async function (assert) {
        await _testTimesheetDisplayTimer(1, false, false, false, assert);
    });

    QUnit.test("timesheet_display_timer does not update the timer when timer_start and timer_pause are not falsy", async function (assert) {
        await _testTimesheetDisplayTimer(
            1,
            now.minus({ hours: 1 }),
            now.minus({ minutes: 30 }),
            false,
            assert
        );
    });

});
