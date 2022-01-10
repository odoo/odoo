/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { makeTestEnv } from "../helpers/mock_env";
import { click, getFixture, patchWithCleanup, triggerEvent, triggerEvents } from "../helpers/utils";
import { registerCleanup } from "../helpers/cleanup";

const { Component, mount } = owl;
const { useState } = owl.hooks;
const { xml } = owl.tags;

const serviceRegistry = registry.category("services");

let env;
let target;
let parent;

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        serviceRegistry.add("hotkey", hotkeyService);
        env = await makeTestEnv();
        target = getFixture();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
        registerCleanup(() => parent.destroy());
    });

    QUnit.module("AutoComplete");

    QUnit.test("can be rendered", async (assert) => {
        class Parent extends Component {}
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete
                value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                onSelect="() => {}"
            />
        `;

        parent = await mount(Parent, { env, target });
        assert.containsOnce(target, ".o-autocomplete");
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");

        await click(target, ".o-autocomplete--input");
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");

        const options = [...target.querySelectorAll(".o-autocomplete--dropdown-item")];
        assert.deepEqual(
            options.map((el) => el.textContent),
            ["World", "Hello"]
        );
    });

    QUnit.test("select option", async (assert) => {
        class Parent extends Component {
            setup() {
                this.state = useState({
                    value: "Hello",
                });
            }
            get sources() {
                return [
                    {
                        options: [{ label: "World" }, { label: "Hello" }],
                    },
                ];
            }
            onSelect(option) {
                this.state.value = option.label;
                assert.step(option.label);
            }
        }
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete
                value="state.value"
                sources="sources"
                onSelect="(option) => this.onSelect(option)"
            />
        `;

        parent = await mount(Parent, { env, target });
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "Hello");

        await click(target, ".o-autocomplete--input");
        await click(target.querySelectorAll(".o-autocomplete--dropdown-item")[0]);
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "World");
        assert.verifySteps(["World"]);

        await click(target, ".o-autocomplete--input");
        await click(target.querySelectorAll(".o-autocomplete--dropdown-item")[1]);
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "Hello");
        assert.verifySteps(["Hello"]);
    });

    QUnit.test("open dropdown on input", async (assert) => {
        class Parent extends Component {}
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete
                value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                onSelect="() => {}"
            />
        `;

        parent = await mount(Parent, { env, target });

        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
        await triggerEvent(target, ".o-autocomplete--input", "input");
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");
    });

    QUnit.test("close dropdown on escape keydown", async (assert) => {
        class Parent extends Component {}
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete
                value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                onSelect="() => {}"
            />
        `;

        parent = await mount(Parent, { env, target });
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");

        await triggerEvents(target, ".o-autocomplete--input", ["focus", "click"]);
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");

        await triggerEvent(target, ".o-autocomplete--input", "keydown", { key: "Escape" });
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
    });

    QUnit.test("scroll outside should close dropdown", async (assert) => {
        class Parent extends Component {}
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete
                value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                onSelect="() => {}"
            />
        `;

        parent = await mount(Parent, { env, target });
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");

        await click(target, ".o-autocomplete--input");
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");

        await triggerEvent(target, null, "scroll");
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
    });

    QUnit.test("scroll inside should keep dropdown open", async (assert) => {
        class Parent extends Component {}
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete
                value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                onSelect="() => {}"
            />
        `;

        parent = await mount(Parent, { env, target });
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");

        await click(target, ".o-autocomplete--input");
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");

        await triggerEvent(target, ".o-autocomplete--dropdown-menu", "scroll");
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");
    });

    QUnit.test("losing focus should close dropdown", async (assert) => {
        class Parent extends Component {}
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete
                value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                onSelect="() => {}"
            />
        `;

        parent = await mount(Parent, { env, target });
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");

        await triggerEvents(target, ".o-autocomplete--input", ["focus", "click"]);
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");

        await triggerEvent(target, ".o-autocomplete--input", "blur");
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
    });
});
