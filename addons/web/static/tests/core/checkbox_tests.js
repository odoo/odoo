/** @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { translatedTerms } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import {
    click,
    getFixture,
    patchWithCleanup,
    mount,
    triggerEvent,
    triggerHotkey,
    nextTick,
} from "@web/../tests/helpers/utils";

const { Component, useState, xml } = owl;
const serviceRegistry = registry.category("services");

let target;

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        serviceRegistry.add("hotkey", hotkeyService);
    });

    QUnit.module("CheckBox");

    QUnit.test("can be rendered", async (assert) => {
        const env = await makeTestEnv();
        await mount(CheckBox, target, { env, props: {} });
        assert.containsOnce(target, '.o-checkbox input[type="checkbox"]');
    });

    QUnit.test("has a slot for translatable text", async (assert) => {
        patchWithCleanup(translatedTerms, { ragabadabadaba: "rugubudubudubu" });
        serviceRegistry.add("localization", makeFakeLocalizationService());
        const env = await makeTestEnv();

        class Parent extends Component {}
        Parent.template = xml`<CheckBox>ragabadabadaba</CheckBox>`;
        Parent.components = { CheckBox };

        await mount(Parent, target, { env });
        assert.containsOnce(target, "div.form-check");
        assert.strictEqual(target.querySelector("div.form-check").textContent, "rugubudubudubu");
    });

    QUnit.test("call onChange prop when some change occurs", async (assert) => {
        const env = await makeTestEnv();

        let value = false;
        class Parent extends Component {
            onChange(checked) {
                value = checked;
            }
        }
        Parent.template = xml`<CheckBox onChange="onChange"/>`;
        Parent.components = { CheckBox };

        await mount(Parent, target, { env });
        assert.containsOnce(target, ".o-checkbox input");
        await click(target.querySelector("input"));
        assert.strictEqual(value, true);
        await click(target.querySelector("input"));
        assert.strictEqual(value, false);
    });

    QUnit.test("can toggle value by pressing ENTER", async (assert) => {
        const env = await makeTestEnv();
        class Parent extends Component {
            setup() {
                this.state = useState({ value: false });
            }
            onChange(checked) {
                this.state.value = checked;
            }
        }
        Parent.template = xml`<CheckBox onChange.bind="onChange" value="state.value"/>`;
        Parent.components = { CheckBox };

        await mount(Parent, target, { env });
        assert.containsOnce(target, ".o-checkbox input");
        assert.notOk(target.querySelector(".o-checkbox input").checked);
        await triggerEvent(target, ".o-checkbox input", "keydown", { key: "Enter" });
        assert.ok(target.querySelector(".o-checkbox input").checked);
        await triggerEvent(target, ".o-checkbox input", "keydown", { key: "Enter" });
        assert.notOk(target.querySelector(".o-checkbox input").checked);
    });

    QUnit.test("toggling through multiple ways", async (assert) => {
        const env = await makeTestEnv();
        class Parent extends Component {
            setup() {
                this.state = useState({ value: false });
            }
            onChange(checked) {
                this.state.value = checked;
                assert.step(`${checked}`);
            }
        }
        Parent.template = xml`<CheckBox onChange.bind="onChange" value="state.value"/>`;
        Parent.components = { CheckBox };
        await mount(Parent, target, { env });
        assert.containsOnce(target, ".o-checkbox input");
        assert.notOk(target.querySelector(".o-checkbox input").checked);

        // Click on div
        assert.verifySteps([]);
        await click(target, ".o-checkbox");
        assert.ok(target.querySelector(".o-checkbox input").checked);
        assert.verifySteps(["true"]);

        // Click on label
        assert.verifySteps([]);
        await click(target, ".o-checkbox > .form-check-label", true);
        assert.notOk(target.querySelector(".o-checkbox input").checked);
        assert.verifySteps(["false"]);

        // Click on input (only possible programmatically)
        assert.verifySteps([]);
        await click(target, ".o-checkbox input");
        assert.ok(target.querySelector(".o-checkbox input").checked);
        assert.verifySteps(["true"]);

        // When somehow applying focus on label, the focus receives it
        // (this is the default behavior from the label)
        target.querySelector(".o-checkbox > .form-check-label").focus();
        await nextTick();
        assert.strictEqual(document.activeElement, target.querySelector(".o-checkbox input"));

        // Press Enter when focus is on input
        assert.verifySteps([]);
        triggerHotkey("Enter");
        await nextTick();
        assert.notOk(target.querySelector(".o-checkbox input").checked);
        assert.verifySteps(["false"]);

        // Pressing Space when focus is on the input is a standard behavior
        // So we simulate it and verify that it will have its standard behavior.
        assert.strictEqual(document.activeElement, target.querySelector(".o-checkbox input"));
        const event = triggerEvent(
            document.activeElement,
            null,
            "keydown",
            { key: "Space" },
            { fast: true }
        );
        assert.ok(!event.defaultPrevented);
        target.querySelector(".o-checkbox input").checked = true;
        assert.verifySteps([]);
        triggerEvent(target, ".o-checkbox input", "change", {}, { fast: true });
        await nextTick();
        assert.ok(target.querySelector(".o-checkbox input").checked);
        assert.verifySteps(["true"]);
    });
});
