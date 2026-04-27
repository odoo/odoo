/** @odoo-module */

import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";
import { TimerReactive } from "@timer/models/timer_reactive";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";

const { DateTime } = luxon;


QUnit.module("timer", (hooks) => {
    let env;
    hooks.beforeEach(async function (assert) {
        registry.category("services").add("orm", ormService, {force: true});
        env = await makeTestEnv();
    });

    QUnit.module("timer_reactive");

    QUnit.test("timer_reactive handle displaying start time", async function (assert) {
        const timerReactive = new TimerReactive(env);
        timerReactive.formatTime();
        assert.strictEqual(timerReactive.time, "00:00:00");

        const currentTime = DateTime.now();
        const timerStart = currentTime.minus({ seconds: 1 });
        timerReactive.computeOffset(currentTime);
        timerReactive.setTimer(0, timerStart, currentTime);
        timerReactive.formatTime();
        assert.strictEqual(timerReactive.time, "00:00:01");
    });

    QUnit.test("timer_reactive handle displaying durations longer than 24h", async function (assert) {
        const timerReactive = new TimerReactive(env);
        const currentTime = DateTime.now();
        const timerStart = currentTime.minus({ days: -2 });
        timerReactive.computeOffset(currentTime);
        timerReactive.setTimer(0, timerStart, currentTime);
        timerReactive.formatTime();
        assert.equal(timerReactive.time, "48:00:00");
    });

});
