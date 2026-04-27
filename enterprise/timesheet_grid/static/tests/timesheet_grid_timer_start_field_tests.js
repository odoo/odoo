/** @odoo-module */

import { serializeDateTime } from "@web/core/l10n/dates";

import { makeView } from "@web/../tests/views/helpers";
import { getFixture } from "@web/../tests/helpers/utils";
import { getServerData, updateArch, setupTestEnv, addFieldsInArch } from "@hr_timesheet/../tests/hr_timesheet_common_tests";
import { registry } from "@web/core/registry";
import { timerService } from "@timer/services/timer_service";

const { DateTime } = luxon;


QUnit.module("timer", (hooks) => {
    let target;
    let viewArguments;
    const now = DateTime.utc();
    hooks.beforeEach(async function (assert) {
        setupTestEnv();

        registry.category("services").add("timer", timerService, { force: true });

        let serverData = getServerData();
        serverData.models["account.analytic.line"].fields["timer_start"] = { string: "Timer Started", type: 'datetime' };
        serverData.models["account.analytic.line"].fields["timer_pause"] = { string: "Timer Paused", type: 'datetime' };
        addFieldsInArch(serverData, ["timer_start", "timer_pause"], "unit_amount");
        updateArch(serverData, { timer_start: "timer_start_field" });
        for (let index = 0; index < serverData.models["account.analytic.line"].records.length; index++) {
            const record = serverData.models["account.analytic.line"].records[index];
            record.timer_pause = index % 2 ? serializeDateTime(now.minus({ hours: 1 })) : false;
            record.timer_start = serializeDateTime(now.minus({ days: 1 }));
        }

        viewArguments = {
            serverData,
            type: "form",
            resModel: "account.analytic.line",
            resId: 1,
            mockRPC(route, { args, method }) {
                if (method === "get_server_time") {
                    return Promise.resolve(serializeDateTime(now));
                }
            },
        };

        target = getFixture();
    });

    QUnit.module("timer_start_field");

    async function _testTimer(expectedRunning, assert) {
        const timerStartInput = target.querySelector('div[name="timer_start"] span');
        const originalValue = timerStartInput.innerText;
        await new Promise(resolve => setTimeout(resolve, 2000));
        const currentValue = timerStartInput.innerText;
        if (expectedRunning) {
          assert.notEqual(originalValue, currentValue, `value should have been updated after 1 second interval`);
        } else {
          assert.strictEqual(originalValue, currentValue, `value should not have been updated after 1 second interval`);
        }
    }

    QUnit.test("timer is running when timer_pause is false", async function (assert) {
        await makeView(viewArguments);
        await _testTimer(true, assert);
    });

    QUnit.test("timer is not running when timer_pause is true", async function (assert) {
        viewArguments.resId = 2;
        await makeView(viewArguments);
        await _testTimer(false, assert);
    });

});
