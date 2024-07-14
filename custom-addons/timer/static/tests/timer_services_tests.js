/** @odoo-module */

import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";

import { makeTestEnv } from "@web/../tests/helpers/mock_env";

import { timerService } from "@timer/services/timer_service";

const { DateTime } = luxon;


QUnit.module("timer", (hooks) => {
    let env;
    hooks.beforeEach(async function (assert) {
        registry.category("services").add("orm", ormService, {force: true});
        registry.category("services").add("timer", timerService, {force: true});
        env = await makeTestEnv();
    });

    QUnit.module("timer_service");

    QUnit.test("timer_service handle displaying durations longer than 24h", async function (assert) {
        const timerService = env.services.timer;
        const currentTime = DateTime.now();
        const timerStart = currentTime.minus({ days: -2 });
        timerService.computeOffset(currentTime);
        timerService.setTimer(0, timerStart, currentTime);
        assert.equal(timerService.timerFormatted, "48:00:00");
    });

});
