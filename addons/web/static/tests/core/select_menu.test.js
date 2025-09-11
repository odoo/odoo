import { expect, test } from "@odoo/hoot";
import { click, edit, press, queryAllTexts, queryOne, queryAll } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    contains,
    editSelectMenu,
    getMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { MainComponentsContainer } from "@web/core/main_components_container";
import { SelectMenu } from "@web/core/select_menu/select_menu";

/**
 * This utils mounts the Component and the MainComponentContainer
 * inside the same App (unlike the default `mountWithCleanup`), this
 * ensures refs and useEffects that target elements inside the menu
 * still work properly.
 */
async function mountSingleApp(ComponentClass, props) {
    class TestComponent extends Component {
        static props = { components: { type: Array } };
        static template = xml`
            <t t-foreach="props.components" t-as="comp" t-key="comp.component.name">
                <t t-component="comp.component" t-props="comp.props"/>
            </t>
        `;
        get defaultComponent() {
            return this.__owl__.bdom.children[0].child.component;
        }
    }

    const comp = await mountWithCleanup(TestComponent, {
        props: {
            components: [
                { component: ComponentClass, props: props || {} },
                { component: MainComponentsContainer, props: {} },
            ],
        },
        noMainContainer: true,
    });

    return comp.defaultComponent;
}

class Parent extends Component {
    static props = ["*"];
    static components = { SelectMenu };
    static template = xml`
        <SelectMenu
            choices="choices"
            value="state.value"
            onSelect.bind="onSelect"
        />
    `;
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

async function open() {
    await click(".o_select_menu_toggler");
    await animationFrame();
    if (getMockEnv().isSmall) {
        // In BottomSheet, the search input is not focused by default.
        // For the following tests, it's easier to expect a focused
        // input for any display of SelectMenu.
        await contains(".o_select_menu_input").click();
    }
    await animationFrame();
}

async function editInput(value) {
    await edit(value);
    await runAllTimers();
    await animationFrame();
}

test("Can be rendered", async () => {
    await mountSingleApp(Parent);

    expect(".o_select_menu").toHaveCount(1);
    expect(".o_select_menu_toggler").toHaveCount(1);

    await open();
    expect(".o_select_menu_menu").toHaveCount(1);
    expect(".o_select_menu_item").toHaveCount(2);
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Hello", "World"]);
});

test("Default value correctly set", async () => {
    await mountSingleApp(Parent);
    expect(".o_select_menu_toggler").toHaveValue("World");
});

test("Selecting a choice calls onSelect and the displayed value is updated", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                groups="groups"
                choices="choices"
                value="state.value"
                onSelect.bind="onSelect"
            />
        `;
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
            expect.step(value);
            this.state.value = value;
        }
    }
    await mountSingleApp(MyParent);

    expect(".o_select_menu_toggler").toHaveValue("World");

    await editSelectMenu(".o_select_menu input", { index: 0 });

    expect(".o_select_menu_toggler").toHaveValue("Hello");
    expect.verifySteps(["hello"]);

    await editSelectMenu(".o_select_menu input", { index: 1 });

    expect(".o_select_menu_toggler").toHaveValue("World");
    expect.verifySteps(["world"]);
});

test("Close dropdown on click outside", async () => {
    await mountSingleApp(Parent);

    expect(".o_select_menu_menu").toHaveCount(0);

    await open();
    expect(".o_select_menu_menu").toHaveCount(1);

    if (getMockEnv().isSmall) {
        await click(".o_bottom_sheet_backdrop");
    } else {
        await click(document.body);
    }
    await animationFrame();

    expect(".o_select_menu_menu").toHaveCount(0);
});

test("Close dropdown on escape keydown", async () => {
    await mountSingleApp(Parent);

    expect(".o_select_menu_menu").toHaveCount(0);

    await open();
    expect(".o_select_menu_menu").toHaveCount(1);

    await press("escape");
    await animationFrame();

    expect(".o_select_menu_menu").toHaveCount(0);
});

test("Search input should be present as a toggler, but cannot be edited if searchable=false", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu choices="choices" searchable="false" />
        `;
        setup() {
            this.choices = [
                { label: "Hello", value: "hello" },
                { label: "World", value: "world" },
            ];
        }
    }
    await mountSingleApp(MyParent);
    await open();
    expect(".o_select_menu_input").not.toBeFocused();
});

test("Search input should be present in a dropdown with a custom toggler", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu choices="choices">
                <span class="select_menu_test">Select something</span>
            </SelectMenu>
        `;
        setup() {
            this.choices = [
                { label: "Hello", value: "hello" },
                { label: "World", value: "world" },
            ];
        }
    }
    await mountSingleApp(MyParent);
    await open();
    expect(".o_select_menu_menu input").toHaveCount(1);
    expect(".o_select_menu_menu input").toBeFocused();
});

test.tags("mobile");
test("Search input should behave as a toggler only and an input should be present in a dropdown on small+touch screen", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu choices="choices" />
        `;
        setup() {
            this.choices = [
                { label: "Hello", value: "hello" },
                { label: "World", value: "world" },
            ];
        }
    }
    await mountSingleApp(MyParent);
    await click(".o_select_menu_toggler");
    await animationFrame();
    expect(".o_select_menu_menu input").toHaveCount(1);
    expect(".o_select_menu_menu input").not.toBeFocused();
});

test("Value with no corresponding choices displays as if no choice was selected", async () => {
    class MyParent extends Component {
        static props = ["*"];
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
    await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler").toHaveValue("");
});

test("Changing value props properly updates the selected choice", async () => {
    class MyParent extends Component {
        static props = ["*"];
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
    const comp = await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler").toHaveValue("A");

    comp.setValue("world");
    await animationFrame();
    expect(".o_select_menu_toggler").toHaveValue("Z");
});

test("Use a null value for choices", async () => {
    class MyParent extends Component {
        static props = ["*"];
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
    const comp = await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler").toHaveValue("Nothing");

    comp.setValue("things");
    await animationFrame();
    expect(".o_select_menu_toggler").toHaveValue("Everything");
});

test("Use an empty string as the value for a choice display the corresponding choice", async () => {
    class MyParent extends Component {
        static props = ["*"];
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
    const comp = await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler").toHaveValue("Empty");

    comp.setValue("full");
    await animationFrame();
    expect(".o_select_menu_toggler").toHaveValue("Full");

    comp.setValue(null);
    await animationFrame();
    expect(".o_select_menu_toggler").toHaveValue("");
});

test("Clear the input calls 'onSelect' with null value and appears only when value is not null", async () => {
    expect.assertions(4);
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                choices="choices"
                value="state.value"
                onSelect.bind="this.onSelect"
            />
        `;
        setup() {
            this.state = useState({ value: "hello" });
            this.choices = [
                { label: "Hello", value: "hello" },
                { label: "World", value: "world" },
            ];
        }
        onSelect(value) {
            expect.step("Cleared");
            expect(value).toBe(null);
            this.state.value = value;
        }
    }
    await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler").toHaveValue("Hello");
    await editSelectMenu(".o_select_menu input", { value: "" });
    expect.verifySteps(["Cleared"]);
    expect(".o_select_menu_toggler").toHaveValue("");
});

test("When the 'required' props is set to true, the input cannot be cleared", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                required="true"
                choices="choices"
                value="state.value"
            />
        `;
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
    const comp = await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler_clear").toHaveCount(0);
    comp.setValue("hello");
    await editSelectMenu(".o_select_menu input", { value: "" });
    expect(".o_select_menu_toggler").toHaveValue("Hello");
});

test("When the 'required' props is set to true, the clear button is not shown", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                required="true"
                choices="choices"
                value="state.value"
            >
                <span class="select_menu_test">Select something</span>
            </SelectMenu>
        `;
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
    const comp = await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler_clear").toHaveCount(0);
    comp.setValue("hello");
    await animationFrame();
    await contains(".o_select_menu_toggler").click();
    expect(".o_select_menu_menu input").toHaveValue("Hello");
    expect(".o_select_menu_toggler_clear").toHaveCount(0);
});

test("Items are sorted based on their label by default", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                choices="choices"
            />
        `;
        setup() {
            this.choices = [
                { label: "Hello", value: "hello" },
                { label: "World", value: "world" },
                { label: "Foo", value: "foo" },
                { label: "Bar", value: "bar" },
            ];
        }
    }
    await mountSingleApp(MyParent);
    await open();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Bar", "Foo", "Hello", "World"]);
});

test("autoSort props set to false", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`<SelectMenu choices="choices" autoSort="false"/>`;
        setup() {
            this.choices = [
                { label: "Hello", value: "hello" },
                { label: "World", value: "world" },
                { label: "Foo", value: "foo" },
                { label: "Bar", value: "bar" },
            ];
        }
    }
    await mountSingleApp(MyParent);
    await open();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Hello", "World", "Foo", "Bar"]);
});

test("Custom toggler using default slot", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu choices="choices">
                <span class="select_menu_test">Select something</span>
            </SelectMenu>
        `;
        setup() {
            this.choices = [
                { label: "Hello", value: "hello" },
                { label: "World", value: "world" },
            ];
        }
    }
    await mountSingleApp(MyParent);
    expect(".select_menu_test").toHaveCount(1);

    await open();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Hello", "World"]);
});

test("Custom choice template using a slot", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu choices="choices">
                <span class="select_menu_test">Select something</span>
                <t t-set-slot="choice" t-slot-scope="choice">
                    <span class="coolClass" t-esc="choice.data.label" />
                </t>
            </SelectMenu>
        `;
        setup() {
            this.choices = [
                { label: "Hello", value: "hello" },
                { label: "World", value: "world" },
            ];
        }
    }
    await mountSingleApp(MyParent);
    await open();
    expect(".coolClass").toHaveCount(2);
    expect(".coolClass:eq(0)").toHaveText("Hello");
});

test("Custom slot for the bottom area sends the current search value", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu choices="choices">
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
        setup() {
            this.choices = [
                { label: "Hello", value: "hello" },
                { label: "World", value: "world" },
            ];
        }
        onClick(value) {
            expect.step(value + " clicked");
        }
    }
    await mountSingleApp(MyParent);
    await open();

    expect(".coolClass").toHaveCount(0);

    await click("input");
    await editInput("coucou");

    expect(".coolClass").toHaveCount(1);

    await click(".coolClass");
    await animationFrame();
    expect.verifySteps(["coucou clicked"]);
});

test("Groups properly added in the select", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`<SelectMenu groups="groups"/>`;
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
    await mountSingleApp(MyParent);
    await open();
    expect(".o_select_menu_group").toHaveCount(1);
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Hello", "World"]);
});

test("Items are properly sorted but still in their respective group", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                choices="this.choices"
                groups="this.groups"
            />
        `;
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
    await mountSingleApp(MyParent);
    await open();
    expect(queryAllTexts(".o_select_menu_item, .o_select_menu_group")).toEqual([
        "Z",
        "X Group A",
        "A",
        "B",
        "X Group B",
        "C",
        "D",
    ]);
});

test("When they are a lot of choices, not all are show at first and scrolling loads more", async () => {
    const scrollSettings = {
        defaultCount: 500,
        increaseAmount: 300,
        distanceBeforeReload: 500,
    };

    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                value="0"
                choices="this.choices"
            />
        `;
        setup() {
            this.scrollSettings = scrollSettings;

            this.choices = [];
            for (let i = 0; i < scrollSettings.defaultCount * 2; i++) {
                this.choices.push({ label: i.toString(), value: i });
            }
        }
    }

    await mountSingleApp(MyParent);
    await open();
    expect(".o_select_menu_item, .o_select_menu_group").toHaveCount(scrollSettings.defaultCount);

    queryOne(".o_select_menu_menu").scrollTo({
        top: queryOne(".o_select_menu_menu").scrollHeight - scrollSettings.distanceBeforeReload,
    });
    await animationFrame();

    expect(".o_select_menu_item, .o_select_menu_group").toHaveCount(
        scrollSettings.defaultCount + scrollSettings.increaseAmount
    );
});

test("When multiSelect is enable, value is an array of values, multiple choices should display as selected and tags should be displayed", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                multiSelect="true"
                value="this.state.value"
                choices="this.choices"
                onSelect.bind="this.onSelect"
            />
        `;
        setup() {
            this.state = useState({ value: [] });
            this.choices = [
                { label: "A", value: "a" },
                { label: "B", value: "b" },
                { label: "C", value: "c" },
            ];
        }

        onSelect(newValue) {
            expect.step(newValue);
            this.state.value = newValue;
        }
    }

    await mountSingleApp(MyParent);
    expect(".o_select_menu .o_tag_badge_text").toHaveCount(0);

    // Select first choice
    await editSelectMenu(".o_select_menu input", { index: 0 });

    expect.verifySteps([["a"]]);

    expect(".o_select_menu .o_tag_badge_text").toHaveCount(1);
    expect(".o_select_menu .o_tag_badge_text").toHaveText("A");

    // Select second choice
    await open();
    expect(".o_select_menu_item:nth-of-type(1).active").toHaveCount(1);

    await editSelectMenu(".o_select_menu input", { index: 1 });
    expect.verifySteps([["a", "b"]]);

    expect(".o_select_menu .o_tag_badge_text").toHaveCount(2);

    await open();
    expect(".o_select_menu_item.active").toHaveCount(2);
});

test("When multiSelect is enable, allow deselecting elements by clicking the selected choices inside the dropdown or by clicking the tags", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                multiSelect="true"
                value="this.state.value"
                choices="this.choices"
                onSelect.bind="this.onSelect"
            />
        `;
        setup() {
            this.state = useState({ value: ["a", "b"] });
            this.choices = [
                { label: "A", value: "a" },
                { label: "B", value: "b" },
                { label: "C", value: "c" },
            ];
        }

        onSelect(newValue) {
            expect.step(newValue);
            this.state.value = newValue;
        }
    }

    await mountSingleApp(MyParent);
    expect(".o_select_menu .o_tag_badge_text").toHaveCount(2);

    await editSelectMenu(".o_select_menu input", { index: 0 });

    expect.verifySteps([["b"]]);

    expect(".o_select_menu .o_tag_badge_text").toHaveCount(1);
    expect(".o_select_menu .o_tag_badge_text").toHaveText("B");

    await open();
    expect(".o_select_menu_item.active").toHaveCount(1);

    await click(".o_tag .o_delete");
    await animationFrame();
    expect.verifySteps([[]]);

    expect(".o_select_menu .o_tag").toHaveCount(0);
});

test.tags("desktop");
test("Navigation is possible from the input when it is focused", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                value="this.state.value"
                choices="this.choices"
                onSelect.bind="this.onSelect"
            />
        `;
        setup() {
            this.state = useState({ value: "b" });
            this.choices = [
                { label: "A", value: "a" },
                { label: "B", value: "b" },
                { label: "C", value: "c" },
            ];
        }

        onSelect(newValue) {
            expect.step(newValue);
            this.state.value = newValue;
        }
    }

    await mountSingleApp(MyParent);
    await open();
    expect(".o_select_menu input").toBeFocused();

    await press("arrowdown");
    await animationFrame();

    expect(".focus").toHaveText("B");
    expect(".o_select_menu input").toBeFocused();

    await press("arrowdown");
    await animationFrame();
    expect(".focus").toHaveText("C");

    await press("arrowdown");
    await press("arrowdown");
    await animationFrame();

    expect(".focus").toHaveText("B");
    await press("enter");
    await animationFrame();
    expect.verifySteps([]);
});

test.tags("desktop");
test("When only one choice is displayed, 'enter' key should select the value", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                value="this.state.value"
                choices="this.choices"
                onSelect.bind="this.onSelect"
            />
        `;
        setup() {
            this.state = useState({ value: "b" });
            this.choices = [
                { label: "A", value: "a" },
                { label: "B", value: "b" },
                { label: "C", value: "c" },
            ];
        }

        onSelect(newValue) {
            expect.step(newValue);
            this.state.value = newValue;
        }
    }

    await mountSingleApp(MyParent);
    await open();
    await editInput("a");

    await press("enter");

    await animationFrame();

    expect.verifySteps(["a"]);
});

test("Props onInput is executed when the search changes", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                choices="state.choices"
                value="state.value"
                onInput.bind="onInput"
                onSelect.bind="onSelect"
            />
        `;
        setup() {
            this.state = useState({
                choices: [{ label: "Hello", value: "hello" }],
                value: "hello",
            });
        }

        onInput(searchString) {
            if (!searchString) {
                expect.step("call with empty search");
                return;
            }
            // This test adds items from the list of choices given by the parent.
            // It can be used as a reference to fetch and load content dynamically to the SelectMenu
            this.state.choices = [
                { label: "Hello", value: "hello" },
                { label: "Coucou", value: "hello2" },
            ];
        }

        onSelect(value) {
            expect.step(value);
            this.state.value = value;
        }
    }

    await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler").toHaveValue("Hello");

    await open();
    expect.verifySteps(["call with empty search"]);
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Hello"]);

    await editInput("cou");
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Coucou"]);

    await editSelectMenu(".o_select_menu input", { index: 0 });
    expect.verifySteps(["hello2"]);
    expect(".o_select_menu_toggler").toHaveValue("Coucou");

    await open();
    expect.verifySteps(["call with empty search"]);
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Coucou", "Hello"]);
});

test("Choices are updated and filtered when props change", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                choices="state.choices"
                value="state.value"
                onInput.bind="onInput"
                onSelect.bind="onSelect"
            />
        `;
        setup() {
            this.state = useState({
                choices: [
                    { label: "Hello", value: "hello" },
                    { label: "Coucou", value: "hello2" },
                ],
                value: "hello",
            });
        }

        onInput(searchString) {
            if (!searchString) {
                return;
            }
            this.state.choices = [
                { label: "Coucou", value: "hello2" },
                { label: "Good afternoon", value: "hello3" },
            ];
        }

        onSelect(value) {
            expect.step(value);
            this.state.value = value;
        }
    }

    await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler").toHaveValue("Hello");

    await open();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Coucou", "Hello"]);

    // edit the input, to trigger onInput and update the props
    await editInput("aft");

    await editSelectMenu(".o_select_menu input", { index: 0 });
    expect.verifySteps(["hello3"]);
    expect(".o_select_menu_toggler").toHaveValue("Good afternoon");

    await open();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Coucou", "Good afternoon"]);
});

test("SelectMenu group items only after being opened", async () => {
    patchWithCleanup(SelectMenu.prototype, {
        filterOptions(args) {
            expect.step("filterOptions");
            super.filterOptions(args);
        },
    });
    class MyParent extends Component {
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

        onInput(searchString) {
            // options have been filtered when typing on the search input",
            if (searchString === "option d") {
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
    await mountSingleApp(MyParent);
    expect.verifySteps([]);

    await open();
    expect(".o_select_menu_menu").toHaveText("Option A\nGroup A\nOption B\nOption C");
    expect.verifySteps(["filterOptions", "filterOptions"]);

    await editInput("option d");

    expect(".o_select_menu_menu").toHaveText("Group B\nOption D");
    expect.verifySteps(["filterOptions", "filterOptions"]);
    await editInput("");

    await animationFrame();

    expect(".o_select_menu_menu").toHaveText("Option A\nGroup A\nOption B\nOption C");
    expect.verifySteps(["filterOptions", "filterOptions"]);
});

test("search value is cleared when reopening the menu", async () => {
    class MyParent extends Component {
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
                value: "hello",
            });
        }

        onInput(searchValue) {
            expect.step("search=" + searchValue);
        }
    }
    await mountSingleApp(MyParent);
    await open();
    expect.verifySteps(["search="]);
    await editInput("a");
    expect.verifySteps(["search=a"]);

    // opening the menu should clear the search input, and trigger onInput with an empty string and update the awaitprops
    await press("escape");
    await animationFrame();
    await open();
    expect.verifySteps(["search="]);
    expect(".o_select_menu input").toHaveValue("");
});

test("Groups can be member of sections", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu choices="choices" groups="groups" sections="sections" />
        `;
        setup() {
            this.choices = [{ label: "Hello", value: "hello" }];
            this.sections = [
                { label: "Group A", name: "sectionA" },
                { label: "Group B", name: "sectionB" },
            ];
            this.groups = [
                {
                    label: "Subgroup 1",
                    choices: [
                        { label: "Option I", value: "optionI" },
                        { label: "Option II", value: "optionII" },
                    ],
                    section: "sectionA",
                },
                {
                    label: "Subgroup 1B",
                    choices: [{ label: "Option B.2", value: "optionB_2" }],
                    section: "sectionB",
                },
                {
                    label: "Subgroup 2",
                    choices: [{ label: "Option 2.I", value: "option2_I" }],
                    section: "sectionA",
                },
            ];
        }
    }
    await mountSingleApp(Parent);
    await open();
    expect(".o_select_menu_group").toHaveCount(5);
    expect(".o_select_menu_item").toHaveCount(5);
    expect(queryAllTexts(".o_select_menu_group")).toEqual([
        "Group A",
        "Subgroup 1",
        "Subgroup 2",
        "Group B",
        "Subgroup 1B",
    ]);
    expect(queryAllTexts(".o_select_menu_item")).toEqual([
        "Hello",
        "Option I",
        "Option II",
        "Option 2.I",
        "Option B.2",
    ]);
    await editInput("option 2");
    expect(queryAllTexts(".o_select_menu_group")).toEqual([
        "Group A",
        "Subgroup 2",
        "Group B",
        "Subgroup 1B",
    ]);
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Option 2.I", "Option B.2"]);
});

test("Can add custom data to choices", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu choices="choices">
                <t t-set-slot="choice" t-slot-scope="choice">
                    <span class="coolClass" t-esc="choice.data.custom" />
                </t>
            </SelectMenu>
        `;
        setup() {
            this.choices = [{ label: "Hello", value: "hello", custom: "hi" }];
        }
    }
    await mountSingleApp(Parent);
    await open();
    expect(".coolClass").toHaveText("hi");
});

test("placeholder added succesfully", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                choices="this.choices"
                value="this.state.value"
                placeholder="'Choose any option'"
                searchPlaceholder="'Search...'"
            />
        `;
        setup() {
            this.choices = [
                { label: "Z", value: "world" },
                { label: "A", value: "company" },
            ];
            this.placeholder = "";
            this.state = useState({ value: "" });
        }
    }
    await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler").toHaveAttribute("placeholder", "Choose any option");
    await open();
    expect(".o_select_menu_toggler").toHaveAttribute("placeholder", "Search...");
});

test("disabled select list", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                choices="this.choices"
                value="this.state.value"
                disabled="true"
            />
        `;
        setup() {
            this.choices = [
                { label: "Z", value: "world" },
                { label: "A", value: "company" },
            ];
            this.state = useState({ value: "" });
        }
    }
    await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler[disabled]").toHaveCount(1);
});

test("Fetch choices", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                value="this.state.value"
                onInput.bind="loadChoice"
                choices="state.choices"
            />
        `;
        setup() {
            this.state = useState({ choices: [] }, { value: "" });
        }
        loadChoice(searchString) {
            if (searchString === "test") {
                this.state.choices = [{ label: "test", value: "test" }];
            } else {
                this.state.choices = [];
            }
        }
    }
    await mountSingleApp(MyParent);
    await open();
    await editInput("test");
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["test"]);
});

test.tags("mobile");
test("In the BottomSheet, a 'Clear' button is present", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                choices="choices"
                value="'test'"
                onSelect.bind="this.onSelect"
            />
        `;
        setup() {
            this.state = useState({ value: "hello" });
            this.choices = [{ label: "Test", value: "test" }];
        }
        onSelect(value) {
            expect.step("Cleared");
            expect(value).toBe(null);
        }
    }
    await mountSingleApp(MyParent);
    await contains(".o_select_menu_toggler").click();
    expect(".o_select_menu_menu .o_clear_button").toHaveCount(1);
    await contains(".o_select_menu_menu .o_clear_button").click();
    expect.verifySteps(["Cleared"]);
});

test("Ensure items are properly sorted", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                groups="state.groups"
                choices="state.choices"
            />
        `;

        setup() {
            this.state = useState({
                choices: [{ label: "item-group-none", value: 0 }],
                groups: [
                    {
                        label: "Group Z",
                        section: "Group Z",
                        choices: [{ label: "item-group-z", value: 1 }],
                    },
                    {
                        label: "Group A",
                        section: "Group A",
                        choices: [{ label: "item-group-a", value: 2 }],
                    },
                    {
                        section: "Z",
                        choices: [{ label: "item-z", value: 3 }],
                    },
                    {
                        section: "World",
                        choices: [{ label: "item-world", value: 5 }],
                    },
                ],
            });
        }
    }

    await mountSingleApp(MyParent);
    await click(".o_select_menu_toggler");
    await animationFrame();

    const elements = [...queryAll(".o_select_menu_group, .o_select_menu_item")];
    expect(elements[0]).toHaveText("item-group-none");
    expect(elements[1]).toHaveText("Group A");
    expect(elements[2]).toHaveText("item-group-a");
    expect(elements[3]).toHaveText("Group Z");
    expect(elements[4]).toHaveText("item-group-z");
    expect(elements[5]).toHaveText("item-world");
    expect(elements[6]).toHaveText("item-z");
});
