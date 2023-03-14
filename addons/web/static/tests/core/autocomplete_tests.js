/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { makeTestEnv } from "../helpers/mock_env";
import {
    click,
    editInput,
    getFixture,
    makeDeferred,
    mount,
    nextTick,
    patchWithCleanup,
    triggerEvent,
    triggerEvents,
} from "../helpers/utils";

import { Component, useState, xml } from "@odoo/owl";

const serviceRegistry = registry.category("services");

let env;
let target;

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        serviceRegistry.add("hotkey", hotkeyService);
        env = await makeTestEnv();
        target = getFixture();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
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

        await mount(Parent, target, { env });
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

        await mount(Parent, target, { env });
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

        await mount(Parent, target, { env });

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

        await mount(Parent, target, { env });
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");

        await triggerEvents(target, ".o-autocomplete--input", ["focus", "click"]);
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");

        await triggerEvent(target, ".o-autocomplete--input", "keydown", { key: "Escape" });
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
    });

    QUnit.test("select input text on first focus", async (assert) => {
        class Parent extends Component {}
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete value="'Bar'" sources="[{ options: [{ label: 'Bar' }] }]" onSelect="() => {}"/>
        `;

        await mount(Parent, target, { env });
        await triggerEvents(target, ".o-autocomplete--input", ["focus", "click"]);
        const el = target.querySelector(".o-autocomplete--input");
        assert.strictEqual(el.value.substring(el.selectionStart, el.selectionEnd), "Bar");
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

        await mount(Parent, target, { env });
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

        await mount(Parent, target, { env });
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

        await mount(Parent, target, { env });
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");

        await triggerEvents(target, ".o-autocomplete--input", ["focus", "click"]);
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");

        await triggerEvent(target, ".o-autocomplete--input", "blur");
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
    });

    QUnit.test("open twice should not display previous results", async (assert) => {
        let def = makeDeferred();
        class Parent extends Component {
            get sources() {
                return [
                    {
                        async options(search) {
                            await def;
                            if (search === "A") {
                                return [{ label: "AB" }, { label: "AC" }];
                            }
                            return [{ label: "AB" }, { label: "AC" }, { label: "BC" }];
                        },
                    },
                ];
            }
        }
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete value="''" sources="sources" onSelect="() => {}"/>
        `;

        await mount(Parent, target, { env });
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");

        await triggerEvent(target, ".o-autocomplete--input", "click");
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");
        assert.containsOnce(target, ".o-autocomplete--dropdown-item");
        assert.containsOnce(target, ".o-autocomplete--dropdown-item .fa-spin"); // loading

        def.resolve();
        await nextTick();
        assert.containsN(target, ".o-autocomplete--dropdown-item", 3);
        assert.containsNone(target, ".fa-spin");

        def = makeDeferred();
        target.querySelector(".o-autocomplete--input").value = "A";
        await triggerEvent(target, ".o-autocomplete--input", "input");
        assert.containsOnce(target, ".o-autocomplete--dropdown-item");
        assert.containsOnce(target, ".o-autocomplete--dropdown-item .fa-spin"); // loading

        def.resolve();
        await nextTick();
        assert.containsN(target, ".o-autocomplete--dropdown-item", 2);
        assert.containsNone(target, ".fa-spin");

        await click(target.querySelector(".o-autocomplete--dropdown-item"));
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");

        // re-open the dropdown -> should not display the previous results
        def = makeDeferred();
        await triggerEvent(target, ".o-autocomplete--input", "click");
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");
        assert.containsOnce(target, ".o-autocomplete--dropdown-item");
        assert.containsOnce(target, ".o-autocomplete--dropdown-item .fa-spin"); // loading
    });

    QUnit.test("press enter on autocomplete with empty source", async (assert) => {
        class Parent extends Component {
            get sources() {
                return [{ options: [] }];
            }
            onSelect() {}
        }
        Parent.components = { AutoComplete };
        Parent.template = xml`<AutoComplete value="''" sources="sources" onSelect="onSelect"/>`;

        await mount(Parent, target, { env });
        assert.containsOnce(target, ".o-autocomplete--input");
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "");
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");

        // click inside the input and press "enter", because why not
        await click(target, ".o-autocomplete--input");
        await triggerEvent(target, ".o-autocomplete--input", "keydown", { key: "Enter" });

        assert.containsOnce(target, ".o-autocomplete--input");
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "");
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
    });

    QUnit.test("press enter on autocomplete with empty source (2)", async (assert) => {
        // in this test, the source isn't empty at some point, but becomes empty as the user
        // updates the input's value.
        class Parent extends Component {
            get sources() {
                const options = (val) => {
                    if (val.length > 2) {
                        return [{ label: "test A" }, { label: "test B" }, { label: "test C" }];
                    }
                    return [];
                };
                return [{ options }];
            }
            onSelect() {}
        }
        Parent.components = { AutoComplete };
        Parent.template = xml`<AutoComplete value="''" sources="sources" onSelect="onSelect"/>`;

        await mount(Parent, target, { env });
        assert.containsOnce(target, ".o-autocomplete--input");
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "");

        // click inside the input and press "enter", because why not
        await editInput(target, ".o-autocomplete--input", "test");
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");
        assert.containsN(
            target,
            ".o-autocomplete--dropdown-menu .o-autocomplete--dropdown-item",
            3
        );

        await editInput(target, ".o-autocomplete--input", "t");
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");

        await triggerEvent(target, ".o-autocomplete--input", "keydown", { key: "Enter" });
        assert.containsOnce(target, ".o-autocomplete--input");
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "t");
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
    });

    QUnit.test("autofocus=true option work as expected", async (assert) => {
        class Parent extends Component {}
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                autofocus="true"
                onSelect="() => {}"
            />
        `;

        await mount(Parent, target, { env });

        assert.strictEqual(target.querySelector(".o-autocomplete input"), document.activeElement);
    });
});
