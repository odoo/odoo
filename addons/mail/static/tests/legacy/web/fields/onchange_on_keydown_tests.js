/** @odoo-module alias=@mail/../tests/web/fields/onchange_on_keydown_tests default=false */
const test = QUnit.test; // QUnit.test()

import {
    editInput,
    getFixture,
    mockTimeout,
    nextTick,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { assertSteps, step } from "@web/../tests/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { dom } from "@web/../tests/legacy_tests/helpers/test_utils";

let serverData;
let target;

QUnit.module("onchange on keydown", {
    async beforeEach() {
        target = getFixture();
        serverData = {
            models: {
                "res.partner": {
                    fields: {
                        id: { type: "integer" },
                        description: { type: "text" },
                        display_name: { type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            description: "",
                            display_name: "first record",
                        },
                    ],
                    onchanges: {
                        description: () => {},
                    },
                },
            },
        };
        setupViewRegistries();
    },
});

test("Test that onchange_on_keydown option triggers the onchange properly", async (assert) => {
    assert.expect(3);
    await makeView({
        type: "form",
        resModel: "res.partner",
        serverData,
        arch: `
                <form>
                    <field name="description" onchange_on_keydown="True" keydown_debounce_delay="0"/>
                </form>`,
        mockRPC(route, params) {
            if (params.method === "onchange") {
                // the onchange will be called twice: at record creation & when keydown is detected
                // the second call should have our description value completed.
                assert.ok(true);
                if (params.args[1] && params.args[1].description === "testing the keydown event") {
                    assert.ok(true);
                }
                return {
                    value: {},
                };
            }
        },
    });
    const textarea = $('textarea[id="description_0"]')[0];
    await dom.click(textarea);
    for (const key of "testing the keydown event") {
        // trigger each key separately to simulate a user typing
        textarea.value = textarea.value + key;
        await dom.triggerEvent(textarea, "input", { key });
    }
    // only trigger the keydown when typing ends to avoid getting a lot of onchange since the
    // delay is set to 0 for test purposes
    // for real use cases there will be a debounce delay set to avoid spamming the event
    await dom.triggerEvent(textarea, "keydown");
    await nextTick();
});

test("Editing a text field with the onchange_on_keydown option disappearing shouldn't trigger a crash", async function () {
    const { execRegisteredTimeouts } = mockTimeout();
    await makeView({
        type: "form",
        resModel: "res.partner",
        serverData,
        resId: 1,
        arch: `
            <form>
                <field name="description" onchange_on_keydown="True" invisible="display_name == 'yop'"/>
                <field name="display_name"/>
            </form>`,
        mockRPC(route, params) {
            if (params.method === "onchange") {
                step("onchange");
            }
        },
    });

    await triggerEvent(target, 'textarea[id="description_0"]', "keydown", { key: "a" });
    await editInput(target, "[name=display_name] input", "yop");
    await execRegisteredTimeouts();
    await assertSteps([]);
});
