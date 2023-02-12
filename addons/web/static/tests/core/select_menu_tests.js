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
                    this.choices = [
                        { label: "Hello", value: "hello" },
                    ];
                    this.groups = [
                        {
                            label: "Group A",
                            choices: [
                                { label: "World", value: "world" },
                            ]
                        }
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
        assert.containsOnce(target, ".o_select_menu_input");
        assert.equal(document.activeElement, target.querySelector(".o_select_menu_input input"));
    });

    QUnit.test(
        "Clear button calls 'onSelect' with null value and appears only when value is null",
        async (assert) => {
            class Parent extends Component {
                setup() {
                    this.state = useState({ value: "Hello" });
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

    QUnit.test("Items are sorted based on their label", async (assert) => {
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
});
