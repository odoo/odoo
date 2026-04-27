/** @odoo-module */

import { serializeDateTime } from "@web/core/l10n/dates";

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { getFixture } from "@web/../tests/helpers/utils";
import { registry } from "@web/core/registry";
import { timerService } from "@timer/services/timer_service";

const { DateTime } = luxon;


QUnit.module("timer", (hooks) => {
    let target;
    let serverData;
    let viewArguments;
    const now = DateTime.utc();
    hooks.beforeEach(async function (assert) {
        serverData = {
            models: {
                "dummy": {
                    fields: {
                        timer_start: {
                            string: "Timer Started",
                            type: "datetime",
                        },
                        timer_pause: {
                            string: "Timer Paused",
                            type: "datetime",
                        },
                    },
                    records: [
                        { id: 1, timer_start: serializeDateTime(now.minus({ days: 1 })), timer_pause: false },
                        { id: 2, timer_start: serializeDateTime(now.minus({ days: 1 })), timer_pause: serializeDateTime(now.minus({ hours: 1 })) },
                    ],
                },
            },
            views: {
                "dummy,false,form": `
                    <form>
                        <group>
                            <group>
                                <field name="timer_start" widget="timer_start_field"/>
                                <field name="timer_pause"/>
                            </group>
                        </group>
                    </form>`,
            },
        };

        setupViewRegistries();
        target = getFixture();

        viewArguments = {
            serverData,
            type: "form",
            resModel: "dummy",
            resId: 1,
            mockRPC(route, { args, method }) {
                if (method === "get_server_time") {
                    return Promise.resolve(serializeDateTime(now));
                }
            },
        };
        registry.category("services").add("timer", timerService, { force: true });

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
          assert.equal(originalValue, currentValue, `value should not have been updated after 1 second interval`);
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
