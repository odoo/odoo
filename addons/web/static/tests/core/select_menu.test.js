import { expect, test } from "@odoo/hoot";
import { click, edit, press, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";

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
}

test("Can be rendered", async () => {
    await mountSingleApp(Parent);

    expect(".o_select_menu").toHaveCount(1);
    expect(".o_select_menu_toggler").toHaveCount(1);

    await open();
    expect(".o_select_menu_menu").toHaveCount(1);
    expect(".o_select_menu_item_label").toHaveCount(2);
    expect(queryAllTexts(".o_select_menu_item_label")).toEqual(["Hello", "World"]);
});

test("Default value correctly set", async () => {
    await mountSingleApp(Parent);
    expect(".o_select_menu_toggler_slot").toHaveText("World");
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

    expect(".o_select_menu_toggler_slot").toHaveText("World");

    await open();
    await click(".o_select_menu_item_label:eq(0)");
    await animationFrame();

    expect(".o_select_menu_toggler_slot").toHaveText("Hello");
    expect.verifySteps(["hello"]);

    await open();
    await click(".o_select_menu_item_label:eq(1)");
    await animationFrame();

    expect(".o_select_menu_toggler_slot").toHaveText("World");
    expect.verifySteps(["world"]);
});

test("Close dropdown on click outside", async () => {
    await mountSingleApp(Parent);

    expect(".o_select_menu_menu").toHaveCount(0);

    await open();
    expect(".o_select_menu_menu").toHaveCount(1);

    await click(document.body);
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

test.tags("desktop")("Search input should be present and auto-focused", async () => {
    await mountSingleApp(Parent);
    await open();
    expect("input.o_select_menu_sticky").toHaveCount(1);
    expect("input.o_select_menu_sticky").toBeFocused();
});

test.tags("mobile")("Search input should be present", async () => {
    await mountSingleApp(Parent);
    await open();
    expect("input.o_select_menu_sticky").toHaveCount(1);
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
    expect(".o_select_menu_toggler_slot").toHaveText("");
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
    expect(".o_select_menu_toggler_slot").toHaveText("A");

    comp.setValue("world");
    await animationFrame();
    expect(".o_select_menu_toggler_slot").toHaveText("Z");
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
    expect(".o_select_menu_toggler_slot").toHaveText("Nothing");

    comp.setValue("things");
    await animationFrame();
    expect(".o_select_menu_toggler_slot").toHaveText("Everything");
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
    expect(".o_select_menu_toggler_slot").toHaveText("Empty");

    comp.setValue("full");
    await animationFrame();
    expect(".o_select_menu_toggler_slot").toHaveText("Full");

    comp.setValue(null);
    await animationFrame();
    expect(".o_select_menu_toggler_slot").toHaveText("");
});

test("Clear button calls 'onSelect' with null value and appears only when value is not null", async () => {
    expect.assertions(5);
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
    expect(".o_select_menu_toggler_clear").toHaveCount(1);
    expect(".o_select_menu_toggler_slot").toHaveText("Hello");

    await click(".o_select_menu_toggler_clear");
    await animationFrame();
    expect.verifySteps(["Cleared"]);
    expect(".o_select_menu_toggler_clear").toHaveCount(0);
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
    await animationFrame();
    expect(".o_select_menu_toggler_slot").toHaveText("Hello");
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
    expect(queryAllTexts(".o_select_menu_item_label")).toEqual(["Bar", "Foo", "Hello", "World"]);
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
    expect(queryAllTexts(".o_select_menu_item_label")).toEqual(["Hello", "World", "Foo", "Bar"]);
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
    expect(queryAllTexts(".o_select_menu_item_label")).toEqual(["Hello", "World"]);
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

test("Custom template for the bottom area of the dropdown using a slot", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
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
    await mountSingleApp(MyParent);
    await open();
    expect(".o_select_menu_bottom_area").toHaveText("2 items selected");
    await click(".o_select_menu_item:nth-child(3)");
    await animationFrame();
    await open();
    expect(".o_select_menu_bottom_area").toHaveText("3 items selected");
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
    await edit("coucou");
    await runAllTimers();
    await animationFrame();

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
    expect(queryAllTexts(".o_select_menu_item_label")).toEqual(["Hello", "World"]);
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

test("When multiSelect is enable, value is an array of values, mutliple choices should display as selected and tags should be displayed", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                multiSelect="true"
                value="this.state.value"
                choices="this.choices"
                onSelect.bind="this.onSelect"
                searchable="false"
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
            expect.step(JSON.stringify(newValue));
            this.state.value = newValue;
        }
    }

    await mountSingleApp(MyParent);
    expect(".o_select_menu .o_tag_badge_text").toHaveCount(0);

    // Select first choice
    await open();
    expect(".o_select_menu_sticky.top-0").toHaveCount(0);
    expect(".o_select_menu_item.o_select_active").toHaveCount(0);

    await click(".o_select_menu_item:nth-child(1)");
    await animationFrame();

    expect.verifySteps([`["a"]`]);

    expect(".o_select_menu .o_tag_badge_text").toHaveCount(1);
    expect(".o_select_menu .o_tag_badge_text").toHaveText("A");

    // Select second choice
    await open();
    expect(".o_select_menu_item:nth-child(1).o_select_active").toHaveCount(1);

    await click(".o_select_menu_item:nth-child(2)");
    await animationFrame();
    expect.verifySteps([`["a","b"]`]);

    expect(".o_select_menu .o_tag_badge_text").toHaveCount(2);

    await open();
    expect(".o_select_menu_item.o_select_active").toHaveCount(2);
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
                searchable="false"
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
            expect.step(JSON.stringify(newValue));
            this.state.value = newValue;
        }
    }

    await mountSingleApp(MyParent);
    expect(".o_select_menu .o_tag_badge_text").toHaveCount(2);

    await open();
    await click(".o_select_menu_item:nth-child(1)");
    await animationFrame();

    expect.verifySteps([`["b"]`]);

    expect(".o_select_menu .o_tag_badge_text").toHaveCount(1);
    expect(".o_select_menu .o_tag_badge_text").toHaveText("B");

    await open();
    expect(".o_select_menu_item.o_select_active").toHaveCount(1);

    await click(".o_tag .o_delete");
    await animationFrame();
    expect.verifySteps(["[]"]);

    expect(".o_select_menu .o_tag").toHaveCount(0);
});

test.tags("desktop")("Navigation is possible from the input when it is focused", async () => {
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
    expect("input.o_select_menu_sticky").toBeFocused();

    await press("arrowdown");
    await animationFrame();

    expect(".focus").toHaveText("A");
    expect("input.o_select_menu_sticky").toBeFocused();

    await press("arrowdown");
    await animationFrame();
    expect(".focus").toHaveText("B");

    await press("arrowdown");
    await press("arrowdown");
    await animationFrame();

    expect(".focus").toHaveText("A");
    await press("enter");
    await animationFrame();
    expect.verifySteps(["a"]);
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
    await edit("a");
    await animationFrame();

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

        onInput() {
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
    expect(".o_select_menu_toggler_slot").toHaveText("Hello");

    await open();
    expect(".o_select_menu_menu").toHaveText("Hello");

    await click("input");
    await edit("cou");
    await runAllTimers();
    await animationFrame();

    expect(".o_select_menu_menu").toHaveText("Coucou");

    await click(".o_select_menu_item_label:eq(0)");
    await animationFrame();

    expect.verifySteps(["hello2"]);
    expect(".o_select_menu_toggler_slot").toHaveText("Coucou");

    await open();
    expect(".o_select_menu_menu").toHaveText("Coucou\nHello");
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

        onInput() {
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
    expect(".o_select_menu_toggler_slot").toHaveText("Hello");

    await open();
    expect(".o_select_menu_menu").toHaveText("Coucou\nHello");

    // edit the input, to trigger onInput and update the props
    await click("input");
    await edit("aft");
    await runAllTimers();
    await animationFrame();

    await click(".o_select_menu_item_label:eq(0await)");
    await animationFrame();
    expect.verifySteps(["hello3"]);
    expect(".o_select_menu_toggler_slot").toHaveText("Good afternoon");

    await open();
    expect(".o_select_menu_menu").toHaveText("Coucou\nGood afternoon");
});

test("SelectMenu group items only after being opened", async () => {
    let count = 0;

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

        onInput() {
            count++;
            // options have been filtered when typing on the search input",
            expect.verifySteps(["filterOptions"]);
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
    await mountSingleApp(MyParent);
    expect.verifySteps([]);

    await open();
    expect(".o_select_menu_menu").toHaveText("Option A\nGroup A\nOption B\nOption C");
    expect.verifySteps(["filterOptions"]);

    await click("input");
    await edit("option d");
    await runAllTimers();
    await animationFrame();

    expect(".o_select_menu_menu").toHaveText("Group B\nOption D");
    expect.verifySteps(["filterOptions"]);
    await edit("");
    await runAllTimers();

    await animationFrame();

    expect(".o_select_menu_menu").toHaveText("Option A\nGroup A\nOption B\nOption C");
    expect.verifySteps(["filterOptions"]);
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
    expect.verifySteps([]);
    await click("input");
    await edit("a");
    await runAllTimers();
    expect.verifySteps(["search=a"]);

    // opening the menu should clear the search string, trigger onInput and update the awaitprops
    await press("escape");
    await animationFrame();
    await open();
    expect.verifySteps(["search="]);
    expect(".o_select_menu_sticky").toHaveValue("");
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
    expect(".o_select_menu_toggler_slot").toHaveText("Choose any option");
    await open();
    expect(".o_select_menu_toggler_slot").toHaveText("Choose any option");
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
    await click("input");
    await edit("test");
    await runAllTimers();
    await animationFrame();
    expect(queryAllTexts(".o_select_menu_item_label")).toEqual(["test"]);
});
