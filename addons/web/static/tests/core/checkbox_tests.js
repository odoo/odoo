/** @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";
import { translatedTerms } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { getFixture, patchWithCleanup, mount, triggerEvent } from "@web/../tests/helpers/utils";

const { Component, xml } = owl;
const serviceRegistry = registry.category("services");

let target;

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
    });

    QUnit.module("CheckBox");

    QUnit.test("can be rendered", async (assert) => {
        const env = await makeTestEnv();
        await mount(CheckBox, { env, target, props: {} });
        assert.containsOnce(target, "div.custom-checkbox");
    });

    QUnit.test("has a slot for translatable text", async (assert) => {
        patchWithCleanup(translatedTerms, { ragabadabadaba: "rugubudubudubu" });
        serviceRegistry.add("localization", makeFakeLocalizationService());
        const env = await makeTestEnv();

        class Parent extends Component {}
        Parent.template = xml`<CheckBox>ragabadabadaba</CheckBox>`;

        const parent = await mount(Parent, { env, target });
        assert.containsOnce(target, "div.custom-checkbox");
        assert.strictEqual(parent.el.innerText, "rugubudubudubu");
    });

    QUnit.test("call onChange prop when some change occurs", async (assert) => {
        const env = await makeTestEnv();

        let value;
        class Parent extends Component {
            onChange(ev) {
                value = ev.target.value;
            }
        }
        Parent.template = xml`<CheckBox onChange="onChange"/>`;

        const parent = await mount(Parent, { env, target });
        assert.containsOnce(target, "div.custom-checkbox");
        const input = parent.el.querySelector("input");
        input.value = "on";
        await triggerEvent(input, null, "change");

        assert.strictEqual(value, "on");
    });
});
