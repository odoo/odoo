/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { makeTestEnv } from "../helpers/mock_env";
import {
    getFixture,
    patchWithCleanup,
    mount,
    click,
    triggerEvent,
    nextTick,
    triggerHotkey,
    editInput,
} from "../helpers/utils";

import { Component, useState, xml } from "@odoo/owl";

const serviceRegistry = registry.category("services");

QUnit.module("Web Components", (hooks) => {
    QUnit.module("SelectMenu");

    let env;
    let target;

    hooks.beforeEach(async () => {
        serviceRegistry.add("hotkey", hotkeyService);
        env = await makeTestEnv();
        target = getFixture();
        patchWithCleanup(browser, {
            setTimeout: (fn) => Promise.resolve().then(fn),
        });
    });

    function getDefaultComponent() {
        class Parent extends Component {
            setup() {
                this.state = useState({ value: "world" });
                this.choices = [
                    { label: "Hello", value: "hello" },
                    { label: "World", value: "world" },
                ];
            }
            onSelect(value) {
                this.state.value = value;
            }
        }
        Parent.components = { SelectMenu };
        Parent.template = xml`
        <SelectMenu
            choices="choices"
            value="state.value"
            onSelect.bind="onSelect"
        />
    `;
        return Parent;
    }

    async function open() {
        if (target.querySelector(".o_select_menu_toggler")) {
            await click(target, ".o_select_menu_toggler");
        } else {
            await click(target, ".o_select_menu");
        }
    }

    function getValue() {
        return target.querySelector(".o_select_menu_toggler_slot").textContent;
    }

    QUnit.test("Can be rendered", async (assert) => {
        const Parent = getDefaultComponent();

        await mount(Parent, target, { env });
        assert.containsOnce(target, ".o_select_menu");
        assert.containsOnce(target, ".o_select_menu_toggler");

        await open();
        assert.containsOnce(target, ".o_select_menu_menu");
        assert.containsN(target, ".o_select_menu_item_label", 2);

        const choices = [...target.querySelectorAll(".o_select_menu_item_label")];
        assert.deepEqual(
            choices.map((el) => el.textContent),
            ["Hello", "World"]
        );
    });

    QUnit.test("Default value correctly set", async (assert) => {
        const Parent = getDefaultComponent();

        await mount(Parent, target, { env });
        assert.strictEqual(getValue(), "World");
    });

    QUnit.test(
        "Selecting a choice calls onSelect and the displayed value is updated",
        async (assert) => {
            class Parent extends Component {
                setup() {
                    this.state = useState({ value: "world" });
                    this.choices = [{ label: "Hello", value: "hello" }];
                    this.groups = [
                        {
                            label: "Group A",
                            choices: [{ label: "World", value: "world" }],
                        },
                    ];
                }

                onSelect(value) {
                    assert.step(value);
                    this.state.value = value;
                }
            }
            Parent.components = { SelectMenu };
            Parent.template = xml`
            <SelectMenu
                groups="groups"
                choices="choices"
                value="state.value"
                onSelect.bind="onSelect"
            />
        `;

            await mount(Parent, target, { env });
            assert.strictEqual(getValue(), "World");

            await open();
            await click(target.querySelectorAll(".o_select_menu_item_label")[0]);
            assert.strictEqual(getValue(), "Hello");
            assert.verifySteps(["hello"]);

            await open();
            await click(target.querySelectorAll(".o_select_menu_item_label")[1]);
            assert.strictEqual(getValue(), "World");
            assert.verifySteps(["world"]);
        }
    );

    QUnit.test("Close dropdown on click outside", async (assert) => {
        const Parent = getDefaultComponent();

        await mount(Parent, target, { env });
        assert.containsNone(target, ".o_select_menu_menu");

        await open();
        assert.containsOnce(target, ".o_select_menu_menu");

        await click(target, null);
        assert.containsNone(target, ".o_select_menu_menu");
    });

    QUnit.test("Close dropdown on escape keydown", async (assert) => {
        const Parent = getDefaultComponent();

        await mount(Parent, target, { env });
        assert.containsNone(target, ".o_select_menu_menu");

        await open();
        assert.containsOnce(target, ".o_select_menu_menu");

        await triggerEvent(target, ".o_select_menu_toggler", "keydown", { key: "Escape" });
        assert.containsNone(target, ".o_select_menu_menu");
    });

    QUnit.test("Search input should be present and auto-focused", async (assert) => {
        const Parent = getDefaultComponent();

        await mount(Parent, target, { env });
        await open();
        assert.containsOnce(target, "input.o_select_menu_sticky");
        assert.equal(document.activeElement, target.querySelector("input.o_select_menu_sticky"));
    });

    QUnit.test(
        "Value with no corresponding choices displays as if no choice was selected",
        async (assert) => {
            class Parent extends Component {
                static components = { SelectMenu };
                static template = xml`
                <SelectMenu
                    choices="this.choices"
                    value="this.state.value"
                />
            `;
                setup() {
                    this.choices = [
                        { label: "World", value: "world" },
                        { label: "Hello", value: "hello" },
                    ];
                    this.state = useState({ value: "coucou" });
                }
                setValue(newValue) {
                    this.state.value = newValue;
                }
            }

            await mount(Parent, target, { env });
            assert.equal(getValue(), "", `The toggler should be empty`);
        }
    );

    QUnit.test("Changing value props properly updates the selected choice", async (assert) => {
        class Parent extends Component {
            static components = { SelectMenu };
            static template = xml`
                <SelectMenu
                    choices="this.choices"
                    value="this.state.value"
                />
            `;
            setup() {
                this.choices = [
                    { label: "Z", value: "world" },
                    { label: "A", value: "company" },
                ];
                this.state = useState({ value: "company" });
            }
            setValue(newValue) {
                this.state.value = newValue;
            }
        }

        const comp = await mount(Parent, target, { env });
        assert.equal(getValue(), "A", `The select value shoud be "A"`);

        comp.setValue("world");
        await nextTick();
        assert.equal(
            getValue(),
            "Z",
            `After changing the value props, the select value shoud be "Z"`
        );
    });

    QUnit.test("Use a null value for choices", async (assert) => {
        class Parent extends Component {
            static components = { SelectMenu };
            static template = xml`
                <SelectMenu
                    choices="this.choices"
                    value="this.state.value"
                />
            `;
            setup() {
                this.choices = [
                    { label: "Nothing", value: null },
                    { label: "Everything", value: "things" },
                ];
                this.state = useState({
                    value: null,
                });
            }
            setValue(newValue) {
                this.state.value = newValue;
            }
        }

        const comp = await mount(Parent, target, { env });
        assert.equal(
            getValue(),
            "Nothing",
            `The select value with an empty string has the "Null" value selected`
        );

        comp.setValue("things");
        await nextTick();
        assert.equal(
            getValue(),
            "Everything",
            `After changing the value props, the select value shoud be "Everything"`
        );
    });

    QUnit.test(
        "Use an empty string as the value for a choice display the corresponding choice",
        async (assert) => {
            class Parent extends Component {
                static components = { SelectMenu };
                static template = xml`
                <SelectMenu
                    choices="this.choices"
                    value="this.state.value"
                />
            `;
                setup() {
                    this.choices = [
                        { label: "Empty", value: "" },
                        { label: "Full", value: "full" },
                    ];
                    this.state = useState({ value: "" });
                }
                setValue(newValue) {
                    this.state.value = newValue;
                }
            }

            const comp = await mount(Parent, target, { env });
            assert.equal(
                getValue(),
                "Empty",
                `The select value with an empty string has the "Empty" value selected`
            );

            comp.setValue("full");
            await nextTick();
            assert.equal(
                getValue(),
                "Full",
                `After changing the value props, the select value shoud be "Full"`
            );

            comp.setValue(null);
            await nextTick();
            assert.equal(
                getValue(),
                "",
                `After changing the value props to a null value, the select has no value selected`
            );
        }
    );

    QUnit.test(
        "Clear button calls 'onSelect' with null value and appears only when value is not null",
        async (assert) => {
            class Parent extends Component {
                setup() {
                    this.state = useState({ value: "hello" });
                    this.choices = [
                        { label: "Hello", value: "hello" },
                        { label: "World", value: "world" },
                    ];
                }
                onSelect(value) {
                    assert.step("Cleared");
                    assert.equal(value, null, "onSelect value should be null");
                    this.state.value = value;
                }
            }
            Parent.components = { SelectMenu };
            Parent.template = xml`
            <SelectMenu
                choices="choices"
                value="state.value"
                onSelect.bind="this.onSelect"
            />
        `;

            await mount(Parent, target, { env });
            assert.containsOnce(target, ".o_select_menu_toggler_clear");
            assert.strictEqual(getValue(), "Hello");

            await click(target.querySelector(".o_select_menu_toggler_clear"));
            assert.verifySteps(["Cleared"]);
            assert.containsNone(target, ".o_select_menu_toggler_clear");
        }
    );

    QUnit.test(
        'When the "required" props is set to true, the clear button is not shown',
        async (assert) => {
            class Parent extends Component {
                setup() {
                    this.state = useState({ value: null });
                    this.choices = [
                        { label: "Hello", value: "hello" },
                        { label: "World", value: "world" },
                    ];
                }
                setValue(newValue) {
                    this.state.value = newValue;
                }
            }
            Parent.components = { SelectMenu };
            Parent.template = xml`
            <SelectMenu
                required="true"
                choices="choices"
                value="state.value"
            />
        `;

            const parent = await mount(Parent, target, { env });
            assert.containsNone(
                target,
                ".o_select_menu_toggler_clear",
                'When the value is not set, there is no "clear" button'
            );

            parent.setValue("hello");
            await nextTick();
            assert.strictEqual(getValue(), "Hello");
            assert.containsNone(
                target,
                ".o_select_menu_toggler_clear",
                'When the value is set, there is no "clear" button'
            );
        }
    );

    QUnit.test("Items are sorted based on their label by default", async (assert) => {
        class Parent extends Component {
            setup() {
                this.choices = [
                    { label: "Hello", value: "hello" },
                    { label: "World", value: "world" },
                    { label: "Foo", value: "foo" },
                    { label: "Bar", value: "bar" },
                ];
            }
        }
        Parent.components = { SelectMenu };
        Parent.template = xml`
                <SelectMenu
                    choices="choices"
                />
            `;

        await mount(Parent, target, { env });
        await open();

        const choices = [...target.querySelectorAll(".o_select_menu_item_label")];
        assert.deepEqual(
            choices.map((el) => el.textContent),
            ["Bar", "Foo", "Hello", "World"]
        );
    });

    QUnit.test("autoSort props set to false", async (assert) => {
        class Parent extends Component {
            setup() {
                this.choices = [
                    { label: "Hello", value: "hello" },
                    { label: "World", value: "world" },
                    { label: "Foo", value: "foo" },
                    { label: "Bar", value: "bar" },
                ];
            }
        }
        Parent.components = { SelectMenu };
        Parent.template = xml`<SelectMenu choices="choices" autoSort="false"/>`;

        await mount(Parent, target, { env });
        await open();

        const choices = [...target.querySelectorAll(".o_select_menu_item_label")];
        assert.deepEqual(
            choices.map((el) => el.textContent),
            ["Hello", "World", "Foo", "Bar"]
        );
    });

    QUnit.test("Custom toggler using default slot", async (assert) => {
        class Parent extends Component {
            setup() {
                this.choices = [
                    { label: "Hello", value: "hello" },
                    { label: "World", value: "world" },
                ];
            }
        }
        Parent.components = { SelectMenu };
        Parent.template = xml`
                <SelectMenu
                    choices="choices"
                >
                    <span class="select_menu_test">Select something</span>
                </SelectMenu>
            `;

        await mount(Parent, target, { env });
        assert.containsOnce(target, ".select_menu_test");

        await open();
        const choicesB = [...target.querySelectorAll(".o_select_menu_item_label")];
        assert.deepEqual(
            choicesB.map((el) => el.textContent),
            ["Hello", "World"]
        );
    });

    QUnit.test("Custom choice template using a slot", async (assert) => {
        class Parent extends Component {
            setup() {
                this.choices = [
                    { label: "Hello", value: "hello" },
                    { label: "World", value: "world" },
                ];
            }
        }
        Parent.components = { SelectMenu };
        Parent.template = xml`
                <SelectMenu
                    choices="choices"
                >
                    <span class="select_menu_test">Select something</span>
                    <t t-set-slot="choice" t-slot-scope="choice">
                        <span class="coolClass" t-esc="choice.data.label" />
                    </t>
                </SelectMenu>
            `;

        await mount(Parent, target, { env });
        await open();
        assert.containsN(target, ".coolClass", 2);
        assert.strictEqual(target.querySelector(".coolClass").textContent, "Hello");
    });

    QUnit.test(
        "Custom template for the bottom area of the dropdown using a slot",
        async (assert) => {
            class Parent extends Component {
                setup() {
                    this.choices = [
                        { label: "Hello", value: "hello" },
                        { label: "World", value: "world" },
                        { label: "How", value: "how" },
                        { label: "Are", value: "are" },
                        { label: "You", value: "you" },
                    ];
                    this.state = useState({ value: ["world", "you"] });
                }
                onSelect(newValue) {
                    this.state.value = newValue;
                }
            }
            Parent.components = { SelectMenu };
            Parent.template = xml`
                <SelectMenu
                    choices="choices"
                    multiSelect="true"
                    onSelect.bind="onSelect"
                    value="state.value"
                >
                    <span class="select_menu_test">Select something</span>
                    <t t-set-slot="bottomArea" t-slot-scope="select">
                    <span class="o_select_menu_bottom_area">
                        <t t-esc="state.value.length"/> items selected
                    </span>
                    </t>
                </SelectMenu>
            `;

            await mount(Parent, target, { env });
            await open();
            assert.strictEqual(
                target.querySelector(".o_select_menu_bottom_area").textContent.trim(),
                "2 items selected"
            );

            await click(target, ".o_select_menu_item:nth-child(3)");
            await open();
            assert.strictEqual(
                target.querySelector(".o_select_menu_bottom_area").textContent.trim(),
                "3 items selected"
            );
        }
    );

    QUnit.test("Custom slot for the bottom area sends the current search value", async (assert) => {
        class Parent extends Component {
            setup() {
                this.choices = [
                    { label: "Hello", value: "hello" },
                    { label: "World", value: "world" },
                ];
            }
            onClick(value) {
                assert.step(value + " clicked");
            }
        }
        Parent.components = { SelectMenu };
        Parent.template = xml`
                <SelectMenu
                    choices="choices"
                >
                    <span class="select_menu_test">Select something</span>
                    <t t-set-slot="bottomArea" t-slot-scope="select">
                        <div t-if="select.data.searchValue" class="px-2">
                            <button class="coolClass btn text-primary" t-on-click="() => this.onClick(select.data.searchValue)">
                                Do something with "<i t-esc="select.data.searchValue" />"
                            </button>
                        </div>
                    </t>
                </SelectMenu>
            `;

        await mount(Parent, target, { env });
        await open();
        assert.containsNone(target, ".coolClass");

        await editInput(target, "input.o_select_menu_sticky", "coucou");
        assert.containsOnce(target, ".coolClass");

        await click(target.querySelector(".coolClass"));
        assert.verifySteps(["coucou clicked"]);
    });

    QUnit.test("Groups properly added in the select", async (assert) => {
        class Parent extends Component {
            setup() {
                this.groups = [
                    {
                        label: "Group",
                        choices: [
                            { label: "Hello", value: "hello" },
                            { label: "World", value: "world" },
                        ],
                    },
                ];
            }
        }
        Parent.components = { SelectMenu };
        Parent.template = xml`
                <SelectMenu
                    groups="groups"
                />
            `;

        await mount(Parent, target, { env });
        await open();

        assert.containsOnce(target, ".o_select_menu_group");

        const choices = [...target.querySelectorAll(".o_select_menu_item_label")];
        assert.deepEqual(
            choices.map((el) => el.textContent),
            ["Hello", "World"]
        );
    });

    QUnit.test("Items are properly sorted but still in their respective group", async (assert) => {
        class Parent extends Component {
            setup() {
                this.choices = [{ label: "Z", value: "z" }];
                this.groups = [
                    {
                        label: "X Group A",
                        choices: [
                            { label: "B", value: "b" },
                            { label: "A", value: "a" },
                        ],
                    },
                    {
                        label: "X Group B",
                        choices: [
                            { label: "C", value: "c" },
                            { label: "D", value: "d" },
                        ],
                    },
                ];
            }
        }
        Parent.components = { SelectMenu };
        Parent.template = xml`
                <SelectMenu
                    choices="this.choices"
                    groups="this.groups"
                />
            `;

        await mount(Parent, target, { env });
        await open();

        const elements = Array.from(
            target.querySelectorAll(".o_select_menu_item, .o_select_menu_group")
        );
        const sortedElements = elements.flatMap((el) => el.children[0].innerText);

        assert.deepEqual(sortedElements, ["Z", "X Group A", "A", "B", "X Group B", "C", "D"]);
    });

    QUnit.test(
        "When they are a lot of choices, not all are show at first and scrolling loads more",
        async (assert) => {
            const scrollSettings = {
                defaultCount: 500,
                increaseAmount: 300,
                distanceBeforeReload: 500,
            };

            class Parent extends Component {
                setup() {
                    this.scrollSettings = scrollSettings;

                    this.choices = [];
                    for (let i = 0; i < scrollSettings.defaultCount * 2; i++) {
                        this.choices.push({ label: i.toString(), value: i });
                    }
                }
            }
            Parent.components = { SelectMenu };
            Parent.template = xml`
                <SelectMenu
                    value="0"
                    choices="this.choices"
                />
            `;

            await mount(Parent, target, { env });
            await open();

            let elements = Array.from(
                target.querySelectorAll(".o_select_menu_item, .o_select_menu_group")
            );
            assert.equal(elements.length, scrollSettings.defaultCount);

            const scrollElement = target.querySelector(".o_select_menu_menu");
            scrollElement.scrollTo({
                top: scrollElement.scrollHeight - scrollSettings.distanceBeforeReload,
            });
            await nextTick();

            elements = Array.from(
                target.querySelectorAll(".o_select_menu_item, .o_select_menu_group")
            );
            assert.equal(
                elements.length,
                scrollSettings.defaultCount + scrollSettings.increaseAmount
            );
        }
    );

    QUnit.test(
        "When multiSelect is enable, value is an array of values, mutliple choices should display as selected and tags should be displayed",
        async (assert) => {
            class Parent extends Component {
                setup() {
                    this.state = useState({ value: [] });
                    this.choices = [
                        { label: "A", value: "a" },
                        { label: "B", value: "b" },
                        { label: "C", value: "c" },
                    ];
                }

                onSelect(newValue) {
                    assert.step(JSON.stringify(newValue));
                    this.state.value = newValue;
                }
            }
            Parent.components = { SelectMenu };
            Parent.template = xml`
                <SelectMenu
                    multiSelect="true"
                    value="this.state.value"
                    choices="this.choices"
                    onSelect.bind="this.onSelect"
                    searchable="false"
                />
            `;

            await mount(Parent, target, { env });
            assert.containsNone(
                target,
                ".o_select_menu .o_tag_badge_text",
                "There should be no selected tags."
            );

            // Select first choice
            await open();
            assert.containsNone(
                target,
                ".o_select_menu_sticky.top-0",
                "Search box is not present."
            );
            assert.containsNone(
                target,
                ".o_select_menu_item.o_select_active",
                "No choice should be selected."
            );

            await click(target, ".o_select_menu_item:nth-child(1)");
            assert.verifySteps([`["a"]`], "Only A should be in the selection list");

            assert.containsN(
                target,
                ".o_select_menu .o_tag_badge_text",
                1,
                "There should be one tag."
            );
            assert.equal(
                target.querySelector(".o_select_menu .o_tag_badge_text").innerText.toLowerCase(),
                "a",
                `The tag's value shoud be "A"`
            );

            // Select second choice
            await open();
            assert.containsOnce(
                target,
                ".o_select_menu_item:nth-child(1).o_select_active",
                "First choice should be selected."
            );

            await click(target, ".o_select_menu_item:nth-child(2)");
            assert.verifySteps([`["a","b"]`], "A and B should be in the selection list");

            assert.containsN(
                target,
                ".o_select_menu .o_tag_badge_text",
                2,
                "There should be two tags."
            );

            await open();
            assert.containsN(
                target,
                ".o_select_menu_item.o_select_active",
                2,
                "Two choices should be selected."
            );
        }
    );

    QUnit.test(
        "When multiSelect is enable, allow deselecting elements by clicking the selected choices inside the dropdown or by clicking the tags",
        async (assert) => {
            class Parent extends Component {
                setup() {
                    this.state = useState({ value: ["a", "b"] });
                    this.choices = [
                        { label: "A", value: "a" },
                        { label: "B", value: "b" },
                        { label: "C", value: "c" },
                    ];
                }

                onSelect(newValue) {
                    assert.step(JSON.stringify(newValue));
                    this.state.value = newValue;
                }
            }
            Parent.components = { SelectMenu };
            Parent.template = xml`
                <SelectMenu
                    multiSelect="true"
                    value="this.state.value"
                    choices="this.choices"
                    onSelect.bind="this.onSelect"
                    searchable="false"
                />
            `;

            await mount(Parent, target, { env });
            assert.containsN(
                target,
                ".o_select_menu .o_tag_badge_text",
                2,
                "There should be two tags."
            );

            await open();
            await click(target, ".o_select_menu_item:nth-child(1)");
            assert.verifySteps([`["b"]`], "Only B should remain in the selection list");

            assert.containsN(
                target,
                ".o_select_menu .o_tag_badge_text",
                1,
                "There should only be one tag."
            );
            assert.equal(
                target.querySelector(".o_select_menu .o_tag_badge_text").innerText.toLowerCase(),
                "b",
                `The tag's value shoud be "B"`
            );

            await open();
            assert.containsOnce(
                target,
                ".o_select_menu_item.o_select_active",
                "Only one choice should be selected."
            );

            await click(target, ".o_tag .o_delete");
            assert.verifySteps(["[]"], "The selection list should be empty");

            assert.containsNone(target, ".o_select_menu .o_tag", "There should be no tags.");
        }
    );

    QUnit.test("Navigation is possible from the input when it is focused", async (assert) => {
        assert.expect(6);

        class Parent extends Component {
            setup() {
                this.state = useState({ value: "b" });
                this.choices = [
                    { label: "A", value: "a" },
                    { label: "B", value: "b" },
                    { label: "C", value: "c" },
                ];
            }

            onSelect(newValue) {
                assert.step(newValue);
                this.state.value = newValue;
            }
        }
        Parent.components = { SelectMenu };
        Parent.template = xml`
                <SelectMenu
                    value="this.state.value"
                    choices="this.choices"
                    onSelect.bind="this.onSelect"
                />
            `;

        await mount(Parent, target, { env });
        await open();
        assert.equal(
            document.activeElement,
            target.querySelector("input.o_select_menu_sticky"),
            "search input is focused by default"
        );

        await triggerHotkey("ArrowDown");
        assert.strictEqual(
            document.activeElement.textContent,
            "A",
            "first item is focused after keyboard navigation"
        );

        await triggerHotkey("ArrowDown");
        assert.strictEqual(document.activeElement.textContent, "B", "second item is now focused");

        await triggerHotkey("ArrowUp");
        await triggerHotkey("ArrowUp");
        assert.equal(
            document.activeElement,
            target.querySelector("input.o_select_menu_sticky"),
            "search input is focused again"
        );

        await triggerHotkey("ArrowDown");
        await triggerHotkey("Enter");
        assert.verifySteps(["a"], "value has been selected after keyboard navigation");
    });

    QUnit.test(
        "When only one choice is displayed, 'enter' key should select the value",
        async (assert) => {
            assert.expect(2);

            class Parent extends Component {
                setup() {
                    this.state = useState({ value: "b" });
                    this.choices = [
                        { label: "A", value: "a" },
                        { label: "B", value: "b" },
                        { label: "C", value: "c" },
                    ];
                }

                onSelect(newValue) {
                    assert.step(newValue);
                    this.state.value = newValue;
                }
            }
            Parent.components = { SelectMenu };
            Parent.template = xml`
                <SelectMenu
                    value="this.state.value"
                    choices="this.choices"
                    onSelect.bind="this.onSelect"
                />
            `;

            await mount(Parent, target, { env });
            await open();
            await editInput(target, "input.o_select_menu_sticky", "a");
            await triggerHotkey("Enter");
            assert.verifySteps(["a"], "value has been selected after keyboard navigation");
        }
    );

    QUnit.test("Props onInput is executed when the search changes", async (assert) => {
        class Parent extends Component {
            setup() {
                this.state = useState({
                    choices: [{ label: "Hello", value: "hello" }],
                    value: "hello",
                });
            }

            onInput() {
                // This test adds items from the list of choices given by the parent.
                // It can be used as a reference to fetch and load content dynamically to the SelectMenu
                this.state.choices = [
                    { label: "Hello", value: "hello" },
                    { label: "Coucou", value: "hello2" },
                ];
            }

            onSelect(value) {
                assert.step(value);
                this.state.value = value;
            }
        }
        Parent.components = { SelectMenu };
        Parent.template = xml`
            <SelectMenu
                choices="state.choices"
                value="state.value"
                onInput.bind="onInput"
                onSelect.bind="onSelect"
            />
        `;

        await mount(Parent, target, { env });
        assert.strictEqual(getValue(), "Hello");

        await open();
        assert.strictEqual(
            target.querySelector(".o_select_menu_menu").textContent,
            "Hello",
            "SelectMenu has only one choice available"
        );

        await editInput(target, "input.o_select_menu_sticky", "cou");
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o_select_menu_menu").textContent,
            "Coucou",
            "SelectMenu now has 'Coucou' available and search is filtered"
        );

        await click(target.querySelectorAll(".o_select_menu_item_label")[0]);
        assert.verifySteps(["hello2"], "added item can be selected");
        assert.strictEqual(getValue(), "Coucou");

        await open();
        assert.strictEqual(
            target.querySelector(".o_select_menu_menu").textContent,
            "CoucouHello",
            "SelectMenu has two choices available"
        );
    });

    QUnit.test("Choices are updated and filtered when props change", async (assert) => {
        class Parent extends Component {
            setup() {
                this.state = useState({
                    choices: [
                        { label: "Hello", value: "hello" },
                        { label: "Coucou", value: "hello2" },
                    ],
                    value: "hello",
                });
            }

            onInput() {
                this.state.choices = [
                    { label: "Coucou", value: "hello2" },
                    { label: "Good afternoon", value: "hello3" },
                ];
            }

            onSelect(value) {
                assert.step(value);
                this.state.value = value;
            }
        }
        Parent.components = { SelectMenu };
        Parent.template = xml`
            <SelectMenu
                choices="state.choices"
                value="state.value"
                onInput.bind="onInput"
                onSelect.bind="onSelect"
            />
        `;

        await mount(Parent, target, { env });
        assert.strictEqual(getValue(), "Hello");

        await open();
        assert.strictEqual(
            target.querySelector(".o_select_menu_menu").textContent,
            "CoucouHello",
            "SelectMenu has two choices available"
        );

        // edit the input, to trigger onInput and update the props
        await editInput(target, "input.o_select_menu_sticky", "aft");
        await nextTick();

        await click(target.querySelectorAll(".o_select_menu_item_label")[0]);
        assert.verifySteps(["hello3"], "added item can be selected");
        assert.strictEqual(getValue(), "Good afternoon");

        await open();
        assert.strictEqual(
            target.querySelector(".o_select_menu_menu").textContent,
            "CoucouGood afternoon",
            "SelectMenu has two updated choices available"
        );
    });

    QUnit.test("SelectMenu group items only after being opened", async (assert) => {
        let count = 0;

        patchWithCleanup(SelectMenu.prototype, {
            filterOptions(args) {
                assert.step("filterOptions");
                super.filterOptions(args);
            },
        });
        class Parent extends Component {
            static components = { SelectMenu };
            static props = ["*"];
            static template = xml`
                <SelectMenu
                    choices="state.choices"
                    groups="state.groups"
                    value="state.value"
                    onInput.bind="onInput"
                />
            `;
            setup() {
                this.state = useState({
                    choices: [{ label: "Option A", value: "optionA" }],
                    groups: [
                        {
                            label: "Group A",
                            choices: [
                                { label: "Option C", value: "optionC" },
                                { label: "Option B", value: "optionB" },
                            ],
                        },
                    ],
                    value: "hello",
                });
            }

            onInput() {
                count++;
                assert.verifySteps(
                    ["filterOptions"],
                    "options have been filtered when typing on the search input"
                );
                if (count === 1) {
                    this.state.choices = [{ label: "Option C", value: "optionC" }];
                    this.state.groups = [
                        {
                            label: "Group B",
                            choices: [{ label: "Option D", value: "optionD" }],
                        },
                    ];
                } else {
                    this.state.choices = [{ label: "Option A", value: "optionA" }];
                    this.state.groups = [
                        {
                            label: "Group A",
                            choices: [
                                { label: "Option C", value: "optionC" },
                                { label: "Option B", value: "optionB" },
                            ],
                        },
                    ];
                }
            }
        }

        await mount(Parent, target, { env });
        assert.verifySteps([], "options have not yet been filtered");

        await open();
        assert.strictEqual(
            target.querySelector(".o_select_menu_menu").textContent,
            "Option AGroup AOption BOption C"
        );
        assert.verifySteps(["filterOptions"], "options have been filtered when the menu opens");

        // edit the input, to trigger onInput and update the props
        await editInput(target, "input.o_select_menu_sticky", "option d");
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o_select_menu_menu").textContent,
            "Group BOption D",
            "options and groups have been recomputed"
        );
        assert.verifySteps(
            ["filterOptions"],
            "options have been filtered since the choices changed"
        );

        // edit the input, to trigger onInput and update the props
        await editInput(target, "input.o_select_menu_sticky", "");
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o_select_menu_menu").textContent,
            "Option AGroup AOption BOption C"
        );
        assert.verifySteps(
            ["filterOptions"],
            "options have been filtered since the choices changed"
        );
    });

    QUnit.test("search value is cleared when reopening the menu", async (assert) => {
        class Parent extends Component {
            setup() {
                this.state = useState({
                    choices: [
                        { label: "Option A", value: "optionA" },
                    ],
                    value: "hello",
                });
            }

            onInput(searchValue) {
                assert.step("search=" + searchValue);
            }
        }
        Parent.components = { SelectMenu };
        Parent.template = xml`
            <SelectMenu
                choices="state.choices"
                groups="state.groups"
                value="state.value"
                onInput.bind="onInput"
            />
        `;

        await mount(Parent, target, { env });
        await open();
        assert.verifySteps([], "onInput props has not been called initially");
        await editInput(target, "input.o_select_menu_sticky", "a");
        assert.verifySteps(["search=a"], "onInput props has been called with the right search string");

        // opening the menu should clear the search string, trigger onInput and update the props
        await triggerEvent(target, ".o_select_menu_toggler", "keydown", { key: "Escape" });
        await open();
        assert.verifySteps(["search="], "onInput props has been called with the empty search string");
        assert.strictEqual(target.querySelector(".o_select_menu_sticky").value, "", "search input is empty");
    });
});
