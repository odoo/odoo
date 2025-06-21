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

        const optionItems = [...target.querySelectorAll(".dropdown-item")];
        assert.deepEqual(
            optionItems.map((el) => ({
                id: el.id,
                role: el.getAttribute("role"),
                "aria-selected": el.getAttribute("aria-selected"),
            })),
            [
                { id: "autocomplete_0_0", role: "option", "aria-selected": "true" },
                { id: "autocomplete_0_1", role: "option", "aria-selected": "false" },
            ]
        );

        const input = target.querySelector(".o-autocomplete--input");
        assert.strictEqual(input.getAttribute("aria-activedescendant"), optionItems[0].id);
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

    QUnit.test("autocomplete with resetOnSelect='true'", async (assert) => {
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
            <div>
                <div class= "test_value" t-esc="state.value"/>
                <AutoComplete
                    value="''"
                    sources="sources"
                    onSelect="(option) => this.onSelect(option)"
                    resetOnSelect="true"
                />
            </div>
        `;

        await mount(Parent, target, { env });
        assert.strictEqual(target.querySelector(".test_value").textContent, "Hello");
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "");

        await editInput(target, ".o-autocomplete--input", "Blip");
        await click(target.querySelectorAll(".o-autocomplete--dropdown-item")[1]);
        assert.strictEqual(target.querySelector(".test_value").textContent, "Hello");
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "");
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

    QUnit.test("cancel result on escape keydown", async (assert) => {
        class Parent extends Component {}
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete
                value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                onSelect="() => {}"
                autoSelect="true"
            />
        `;

        await mount(Parent, target, { env });
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "Hello");

        await triggerEvents(target, ".o-autocomplete--input", ["focus", "click"]);
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");
        await editInput(target, ".o-autocomplete--input", "H");

        await triggerEvent(target, ".o-autocomplete--input", "keydown", { key: "Escape" });
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "Hello");
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

    QUnit.test("scroll outside should cancel result", async (assert) => {
        class Parent extends Component {}
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete
                value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                onSelect="() => {}"
                autoSelect="true"
            />
        `;

        await mount(Parent, target, { env });
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "Hello");

        await click(target, ".o-autocomplete--input");
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");
        await editInput(target, ".o-autocomplete--input", "H");

        await triggerEvent(target, null, "scroll");
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "Hello");
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

    QUnit.test("losing focus should cancel result", async (assert) => {
        class Parent extends Component {}
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete
                value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                onSelect="() => {}"
                autoSelect="true"
            />
        `;

        await mount(Parent, target, { env });
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "Hello");

        await triggerEvents(target, ".o-autocomplete--input", ["focus", "click"]);
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");
        await editInput(target, ".o-autocomplete--input", "H");

        await triggerEvent(target, "", "pointerdown");
        await triggerEvent(target, ".o-autocomplete--input", "blur");
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "Hello");
    });

    QUnit.test("click out after clearing input", async (assert) => {
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
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "Hello");

        await triggerEvents(target, ".o-autocomplete--input", ["focus", "click"]);
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");
        await editInput(target, ".o-autocomplete--input", "");

        await triggerEvent(target, "", "pointerdown");
        await triggerEvent(target, ".o-autocomplete--input", "blur");
        assert.containsNone(target, ".o-autocomplete--dropdown-menu");
        assert.strictEqual(target.querySelector(".o-autocomplete--input").value, "");
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

    QUnit.test("autocomplete in edition keep edited value before select option", async (assert) => {
        class Parent extends Component {
            setup() {
                this.state = useState({ value: "Hello" });
            }

            onClick() {
                this.state.value = "My Click";
            }

            onSelect() {
                this.state.value = "My Selection";
            }
        }
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <button class="myButton" t-on-click="onClick" />
            <AutoComplete value="this.state.value"
            sources="[{ options: [{ label: 'My Selection' }] }]"
            onSelect.bind="onSelect"
            />
        `;

        await mount(Parent, target, { env });
        const input = target.querySelector(".o-autocomplete input");
        input.value = "Yolo";
        await triggerEvent(input, null, "input");
        assert.strictEqual(target.querySelector(".o-autocomplete input").value, "Yolo");

        await click(target, ".myButton");
        assert.strictEqual(target.querySelector(".o-autocomplete input").value, "Yolo");

        // Leave inEdition mode when selecting an option
        await click(target.querySelector(".o-autocomplete input"));
        await click(target.querySelectorAll(".o-autocomplete--dropdown-item")[0]);
        assert.strictEqual(target.querySelector(".o-autocomplete input").value, "My Selection");

        await click(target, ".myButton");
        assert.strictEqual(target.querySelector(".o-autocomplete input").value, "My Click");
    });

    QUnit.test("autocomplete in edition keep edited value before blur", async (assert) => {
        let count = 0;
        class Parent extends Component {
            setup() {
                this.state = useState({ value: "Hello" });
            }

            onClick() {
                this.state.value = `My Click ${count++}`;
            }
        }
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <button class="myButton" t-on-click="onClick" />
            <AutoComplete value="this.state.value"
            sources="[]"
            onSelect="() => {}"
            />
        `;

        await mount(Parent, target, { env });
        let input = target.querySelector(".o-autocomplete input");
        input.value = "";
        await triggerEvent(input, null, "input");
        assert.strictEqual(target.querySelector(".o-autocomplete input").value, "");

        await click(target, ".myButton");
        assert.strictEqual(target.querySelector(".o-autocomplete input").value, "");

        // Leave inEdition mode when blur the input
        input = target.querySelector(".o-autocomplete input");
        await triggerEvent(input, null, "blur");
        await nextTick();
        assert.strictEqual(target.querySelector(".o-autocomplete input").value, "");

        await click(target, ".myButton");
        assert.strictEqual(target.querySelector(".o-autocomplete input").value, "My Click 1");
    });

    QUnit.test("correct sequence of blur, focus and select [REQUIRE FOCUS]", async (assert) => {
        class Parent extends Component {
            setup() {
                this.state = useState({
                    value: "",
                });
            }
            get sources() {
                return [
                    {
                        options: [{ label: "World" }, { label: "Hello" }],
                    },
                ];
            }
            onChange() {
                assert.step("change");
            }
            onSelect(option) {
                target.querySelector(".o-autocomplete--input").value = option.label;
                assert.step("select " + option.label);
            }
            onBlur() {
                assert.step("blur");
            }
        }
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete
                value="state.value"
                sources="sources"
                onSelect.bind="onSelect"
                onBlur.bind="onBlur"
                onChange.bind="onChange"
                autoSelect="true"
            />
        `;
        await mount(Parent, target, { env });
        assert.containsOnce(target, ".o-autocomplete--input");
        const input = target.querySelector(".o-autocomplete--input");
        await click(input);
        input.focus();

        // Navigate suggestions using arrow keys
        const optionItems = [...target.querySelectorAll(".dropdown-item")];
        assert.deepEqual(
            optionItems.map((el) => ({
                id: el.id,
                role: el.getAttribute("role"),
                "aria-selected": el.getAttribute("aria-selected"),
            })),
            [
                { id: "autocomplete_0_0", role: "option", "aria-selected": "true" },
                { id: "autocomplete_0_1", role: "option", "aria-selected": "false" },
            ]
        );
        assert.strictEqual(input.getAttribute("aria-activedescendant"), optionItems[0].id);
        await triggerEvent(target, ".o-autocomplete--input", "keydown", { key: "arrowdown" });
        assert.deepEqual(
            optionItems.map((el) => ({
                id: el.id,
                role: el.getAttribute("role"),
                "aria-selected": el.getAttribute("aria-selected"),
            })),
            [
                { id: "autocomplete_0_0", role: "option", "aria-selected": "false" },
                { id: "autocomplete_0_1", role: "option", "aria-selected": "true" },
            ]
        );
        assert.strictEqual(input.getAttribute("aria-activedescendant"), optionItems[1].id);

        // Start typing hello and click on the result
        await triggerEvent(target, ".o-autocomplete--input", "keydown", { key: "h" });
        input.value = "h";
        await triggerEvent(input, "", "input");
        assert.containsOnce(target, ".o-autocomplete--dropdown-menu");
        const pointerdownEvent = await triggerEvent(
            target.querySelectorAll(".o-autocomplete--dropdown-item")[1],
            "",
            "pointerdown"
        );
        assert.strictEqual(pointerdownEvent.defaultPrevented, false);
        const mousedownEvent = await triggerEvent(
            target.querySelectorAll(".o-autocomplete--dropdown-item")[1],
            "",
            "mousedown"
        );
        assert.strictEqual(mousedownEvent.defaultPrevented, false);
        await triggerEvent(input, "", "change");
        await triggerEvent(input, "", "blur");
        await triggerEvent(
            target.querySelectorAll(".o-autocomplete--dropdown-item")[1],
            "",
            "click"
        );
        assert.verifySteps(["change", "select Hello"]);
        assert.strictEqual(input, document.activeElement);

        // Clear input and focus out
        await triggerEvent(input, "", "keydown", { key: "Backspace" });
        input.value = "";
        await triggerEvent(input, "", "input");
        await triggerEvent(target, "", "pointerdown");
        await triggerEvent(input, "", "change");
        await triggerEvent(input, "", "blur");
        await triggerEvent(target, "", "click");
        assert.verifySteps(["change", "blur"]);
    });

    QUnit.test("autocomplete always closes on click away [REQUIRE FOCUS]", async (assert) => {
        class Parent extends Component {
            setup() {
                this.state = useState({
                    value: "",
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
                target.querySelector(".o-autocomplete--input").value = option.label;
            }
        }
        Parent.components = { AutoComplete };
        Parent.template = xml`
            <AutoComplete
                value="state.value"
                sources="sources"
                onSelect.bind="onSelect"
                autoSelect="true"
            />
        `;
        await mount(Parent, target, { env });
        assert.containsOnce(target, ".o-autocomplete--input");
        const input = target.querySelector(".o-autocomplete--input");
        await click(input);
        assert.containsN(target, ".o-autocomplete--dropdown-item", 2);
        const pointerdownEvent = await triggerEvent(
            target.querySelectorAll(".o-autocomplete--dropdown-item")[1],
            "",
            "pointerdown"
        );
        assert.strictEqual(pointerdownEvent.defaultPrevented, false);
        const mousedownEvent = await triggerEvent(
            target.querySelectorAll(".o-autocomplete--dropdown-item")[1],
            "",
            "mousedown"
        );
        assert.strictEqual(mousedownEvent.defaultPrevented, false);
        await triggerEvent(input, "", "blur");
        await triggerEvent(target, "", "pointerup");
        await triggerEvent(target, "", "mouseup");
        assert.containsN(target, ".o-autocomplete--dropdown-item", 2);
        await triggerEvent(target, "", "pointerdown");
        assert.containsNone(target, ".o-autocomplete--dropdown-item");
    });

    QUnit.test("autocomplete trim spaces for search", async (assert) => {
        class Parent extends Component {
            setup() {
                this.state = useState({
                    value: " World",
                });
            }
            get sources() {
                return [
                    {
                        options(search) {
                            return [{ label: "World" }, { label: "Hello" }].filter(({ label }) =>
                                label.startsWith(search)
                            );
                        },
                    },
                ];
            }
        }
        Parent.template = xml`
            <AutoComplete value="state.value" sources="sources" onSelect="() => {}"/>
        `;
        Parent.props = ["*"];
        Parent.components = { AutoComplete };
        await mount(Parent, target, { env });
        await click(target, `.o-autocomplete input`);
        assert.deepEqual(
            [...target.querySelectorAll(`.o-autocomplete--dropdown-item`)].map(
                (el) => el.textContent
            ),
            ["World", "Hello"]
        );
    });
});
