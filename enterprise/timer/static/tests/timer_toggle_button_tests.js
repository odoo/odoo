/** @odoo-module */

import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { click, getFixture, mount, nextTick } from "@web/../tests/helpers/utils";

import { TimerToggleButton } from "@timer/component/timer_toggle_button/timer_toggle_button";


QUnit.module("timer", (hooks) => {
    let target;
    hooks.beforeEach(async function (assert) {
        target = getFixture();
        registry.category("services").add("orm", ormService, { force: true });
    });

    QUnit.module("TimerToggleButton");

    async function _test_timer_toggle_button(testState, assert) {
        const action = `action_timer_${testState ? "stop" : "start"}`;
        const icon = testState ? "stop" : "play";
        const env = await makeTestEnv({
            async mockRPC(route, args) {
                if (args.method === action) {
                    assert.step(action);
                }
                return true;
            },
        });
        const props = {
            name: "timer",
            context: {},
            record: {
                resModel: "dummy",
                model: {
                    load() {
                        assert.step("load");
                    },
                },
                data: {
                    timer: testState,
                },
            },
        };
        await mount(TimerToggleButton, target, { env, props: props });
        await nextTick();
        assert.hasClass(target.querySelector("button i"), `fa-${icon}-circle`, "correct icon is used");
        await click(target, "button");
        assert.verifySteps([action, "load"], "correct action is called and record is reloaded and view is refreshed");
    }

    QUnit.test("TimerToggleButton true value state test", async function (assert) {
        await _test_timer_toggle_button(true, assert);
    });

    QUnit.test("TimerToggleButton false value state test", async function (assert) {
        await _test_timer_toggle_button(false, assert);
    });

});
