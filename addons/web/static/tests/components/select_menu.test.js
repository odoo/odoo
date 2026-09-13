// @ts-check

import { expect, test } from "@odoo/hoot";
import {
    click,
    edit,
    press,
    queryAll,
    queryAllTexts,
    queryOne,
    queryValue,
} from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, onRendered, onWillRender, useState, xml } from "@odoo/owl";
import {
    contains,
    editSelectMenu,
    getMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { DropdownPopover } from "@web/components/dropdown/_behaviours/dropdown_popover";
import { SelectMenu } from "@web/components/select_menu/select_menu";
import { MainComponentsContainer } from "@web/ui/main_components_container";

test("an open menu follows sorting and section changes", async () => {
    class Host extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`<SelectMenu t-props="state"/>`;
        setup() {
            this.state = useState({
                autoSort: true,
                groups: [
                    {
                        section: "a",
                        choices: [
                            { value: 2, label: "Zulu" },
                            { value: 1, label: "Alpha" },
                        ],
                    },
                    { section: "b", choices: [{ value: 3, label: "Beta" }] },
                ],
                sections: [
                    { name: "a", label: "First" },
                    { name: "b", label: "Second" },
                ],
            });
        }
    }
    const host = await mountWithCleanup(Host);
    await open();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Alpha", "Zulu", "Beta"]);
    host.state.autoSort = false;
    await animationFrame();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Zulu", "Alpha", "Beta"]);
    host.state.sections.reverse();
    await animationFrame();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Beta", "Zulu", "Alpha"]);
});

async function mountSingleApp(
    /** @type {any} */ ComponentClass,
    /** @type {any} */ props = undefined,
) {
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
    onSelect(/** @type {any} */ value) {
        this.state.value = value;
    }
}

async function open() {
    await click(".o_select_menu_toggler");
    await animationFrame();
    if (getMockEnv().isSmall) {
        await contains(".o_select_menu_input").click();
    }
    await animationFrame();
}

async function editInput(/** @type {any} */ value) {
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

        onSelect(/** @type {any} */ value) {
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

test("Escape while a debounced search is pending keeps the dropdown closed", async () => {
    await mountSingleApp(Parent);

    await open();
    expect(".o_select_menu_menu").toHaveCount(1);

    await edit("he", { confirm: false });
    await press("escape");
    await animationFrame();
    expect(".o_select_menu_menu").toHaveCount(0);

    await runAllTimers();
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
        setValue(/** @type {any} */ newValue) {
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
        setValue(/** @type {any} */ newValue) {
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
        setValue(/** @type {any} */ newValue) {
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
        setValue(/** @type {any} */ newValue) {
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
        onSelect(/** @type {any} */ value) {
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
        setValue(/** @type {any} */ newValue) {
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
        setValue(/** @type {any} */ newValue) {
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
    expect(queryAllTexts(".o_select_menu_item")).toEqual([
        "Bar",
        "Foo",
        "Hello",
        "World",
    ]);
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
    expect(queryAllTexts(".o_select_menu_item")).toEqual([
        "Hello",
        "World",
        "Foo",
        "Bar",
    ]);
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
        onClick(/** @type {any} */ value) {
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

            /** @type {any[]} */
            this.choices = [];
            for (let i = 0; i < scrollSettings.defaultCount * 2; i++) {
                this.choices.push({ label: i.toString(), value: i });
            }
        }
    }

    await mountSingleApp(MyParent);
    await open();
    expect(".o_select_menu_item, .o_select_menu_group").toHaveCount(
        scrollSettings.defaultCount,
    );

    queryOne(".o_select_menu_menu").scrollTo({
        top:
            queryOne(".o_select_menu_menu").scrollHeight -
            scrollSettings.distanceBeforeReload,
    });
    await animationFrame();
    await animationFrame();

    expect(".o_select_menu_item, .o_select_menu_group").toHaveCount(
        scrollSettings.defaultCount + scrollSettings.increaseAmount,
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

        onSelect(/** @type {any} */ newValue) {
            expect.step(newValue);
            this.state.value = newValue;
        }
    }

    await mountSingleApp(MyParent);
    expect(".o_select_menu .o_tag_badge_text").toHaveCount(0);

    await editSelectMenu(".o_select_menu input", { index: 0 });

    expect.verifySteps([["a"]]);

    expect(".o_select_menu .o_tag_badge_text").toHaveCount(1);
    expect(".o_select_menu .o_tag_badge_text").toHaveText("A");

    await open();
    expect(".o_select_menu_item:nth-of-type(1).selected").toHaveCount(1);

    await editSelectMenu(".o_select_menu input", { index: 1 });
    expect.verifySteps([["a", "b"]]);

    expect(".o_select_menu .o_tag_badge_text").toHaveCount(2);

    await open();
    expect(".o_select_menu_item.selected").toHaveCount(2);
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

        onSelect(/** @type {any} */ newValue) {
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
    expect(".o_select_menu_item.selected").toHaveCount(1);

    await click(".o_tag .o_delete");
    await animationFrame();
    expect.verifySteps([[]]);

    expect(".o_select_menu .o_tag").toHaveCount(0);
});

test("When multiSelect is enable, the clear button calls 'onSelect' with an empty array", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                multiSelect="true"
                choices="choices"
                value="state.value"
                onSelect.bind="this.onSelect"
            >
                <span class="select_menu_test">Select tags</span>
            </SelectMenu>
        `;
        setup() {
            this.state = useState({ value: ["a", "b"] });
            this.choices = [
                { label: "A", value: "a" },
                { label: "B", value: "b" },
                { label: "C", value: "c" },
            ];
        }
        onSelect(/** @type {any} */ newValue) {
            expect.step(newValue);
            this.state.value = newValue;
        }
    }

    await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler_clear").toHaveCount(1);

    await click(".o_select_menu_toggler_clear");
    await animationFrame();
    expect.verifySteps([[]]);

    expect(".o_select_menu").toHaveCount(1);
    expect(".o_select_menu_toggler_clear").toHaveCount(0);
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

        onSelect(/** @type {any} */ newValue) {
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

        onSelect(/** @type {any} */ newValue) {
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

        onInput(/** @type {any} */ searchString) {
            if (!searchString) {
                expect.step("call with empty search");
                return;
            }
            this.state.choices = [
                { label: "Hello", value: "hello" },
                { label: "Coucou", value: "hello2" },
            ];
        }

        onSelect(/** @type {any} */ value) {
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

        onInput(/** @type {any} */ searchString) {
            if (!searchString) {
                return;
            }
            this.state.choices = [
                { label: "Coucou", value: "hello2" },
                { label: "Good afternoon", value: "hello3" },
            ];
        }

        onSelect(/** @type {any} */ value) {
            expect.step(value);
            this.state.value = value;
        }
    }

    await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler").toHaveValue("Hello");

    await open();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Coucou", "Hello"]);

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

        onInput(/** @type {any} */ searchString) {
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
    expect.verifySteps(["filterOptions"]);
    await editInput("");

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

        onInput(/** @type {any} */ searchValue) {
            expect.step("search=" + searchValue);
        }
    }
    await mountSingleApp(MyParent);
    await open();
    expect.verifySteps(["search="]);
    await editInput("a");
    expect.verifySteps(["search=a"]);

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
    expect(".o_select_menu_toggler").toHaveAttribute(
        "placeholder",
        "Choose any option",
    );
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
            this.state = useState({ choices: [], value: "" });
        }
        loadChoice(/** @type {any} */ searchString) {
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
        onSelect(/** @type {any} */ value) {
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

test.tags("mobile");
test("In the BottomSheet, the 'Clear' button of a multiSelect calls 'onSelect' with an empty array", async () => {
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`
            <SelectMenu
                multiSelect="true"
                choices="choices"
                value="state.value"
                onSelect.bind="this.onSelect"
            />
        `;
        setup() {
            this.state = useState({ value: ["hello"] });
            this.choices = [
                { label: "Hello", value: "hello" },
                { label: "World", value: "world" },
            ];
        }
        onSelect(/** @type {any} */ value) {
            expect.step("Cleared");
            expect(value).toEqual([]);
            this.state.value = value;
        }
    }
    await mountSingleApp(MyParent);
    await contains(".o_select_menu_toggler").click();
    expect(".o_select_menu_menu .o_clear_button").toHaveCount(1);
    await contains(".o_select_menu_menu .o_clear_button").click();
    expect.verifySteps(["Cleared"]);

    await animationFrame();
    await contains(".o_select_menu_toggler").click();
    expect(".o_select_menu_menu .o_clear_button").toHaveCount(0);
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

test("a group header is never reported as the selected option", async () => {
    /** @type {any} */
    let instance;
    class Probe extends SelectMenu {
        setup() {
            super.setup();
            instance = this;
        }
    }
    await mountSingleApp(Probe, {
        groups: [
            { label: "Group A", choices: [{ value: "a", label: "A" }] },
            { label: "Group B", choices: [{ value: "b", label: "B" }] },
        ],
        onSelect: () => {},
    });
    await click(".o_select_menu_toggler");
    await animationFrame();

    const header = instance.filtered.choices.find(
        (/** @type {any} */ choice) => choice.isGroup,
    );
    expect(Boolean(header)).toBe(true);
    expect(instance.isOptionSelected(header)).toBe(false);
    expect(instance.getSelectedOptionIndex()).toBe(-1);
});

test("an emptied choices prop does not show 'No results' next to grouped options", async () => {
    /** @type {() => void} */
    let clearChoices;
    class Parent extends Component {
        static components = { SelectMenu };
        static props = {};
        static template = xml`
            <SelectMenu choices="state.choices" groups="groups" onSelect="() => {}"/>`;
        setup() {
            this.state = useState({ /** @type {any[]} */ choices: [] });
            this.groups = [
                { label: "Group A", choices: [{ value: "a", label: "Alpha" }] },
            ];
            clearChoices = () => (this.state.choices = []);
        }
    }
    await mountSingleApp(Parent, {});

    await click(".o_select_menu_toggler");
    await runAllTimers();
    await animationFrame();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Alpha"]);
    expect(".o_select_menu_menu p.fst-italic").toHaveCount(0);

    clearChoices();
    await animationFrame();

    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Alpha"]);
    expect(".o_select_menu_menu p.fst-italic").toHaveCount(0);
});

test("sections render in the order they were declared", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`<SelectMenu choices="[]" groups="groups" sections="sections"/>`;
        setup() {
            this.sections = [
                { label: "Zebra", name: "zzz" },
                { label: "Alpha", name: "aaa" },
            ];
            this.groups = [
                { choices: [{ label: "In Alpha", value: "a" }], section: "aaa" },
                { choices: [{ label: "In Zebra", value: "z" }], section: "zzz" },
            ];
        }
    }
    await mountSingleApp(Parent);
    await open();
    expect(queryAllTexts(".o_select_menu_group")).toEqual(["Zebra", "Alpha"]);
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["In Zebra", "In Alpha"]);
});

test.tags("desktop");
test("a searchable menu publishes its active choice via aria-activedescendant", async () => {
    await mountSingleApp(SelectMenu, {
        choices: [
            { label: "Alpha", value: "a" },
            { label: "Beta", value: "b" },
        ],
        searchable: true,
        onSelect: () => {},
    });
    await click(".o_select_menu_toggler");
    await animationFrame();
    await press("ArrowDown");
    await animationFrame();

    const input = queryOne(".o_select_menu_input");
    expect(document.activeElement).toBe(input);
    expect(input).toHaveAttribute("role", "combobox");
    expect(input).toHaveAttribute("aria-expanded", "true");
    const listbox = queryOne("[role=listbox]");
    expect(input).toHaveAttribute("aria-controls", listbox.id);
    expect(listbox).not.toBe(queryOne(".o_select_menu_menu"));
    expect(queryOne(".o_select_menu_menu")).not.toHaveAttribute("role", "listbox");

    const active = input.getAttribute("aria-activedescendant");
    expect(active).not.toBe(null);
    const activeEl = document.getElementById(active);
    expect(activeEl).not.toBe(null);
    expect(activeEl).toHaveClass("focus");
    expect(activeEl).toHaveAttribute("role", "option");
    expect(activeEl).toHaveAttribute("aria-selected", "true");
    expect(queryOne(".o_select_menu_menu").getAttribute("aria-activedescendant")).toBe(
        null,
    );
});

test.tags("mobile");
test("a searchable BottomSheet publishes its active choice once its input is focused", async () => {
    await mountSingleApp(SelectMenu, {
        choices: [
            { label: "Alpha", value: "a" },
            { label: "Beta", value: "b" },
        ],
        searchable: true,
        onSelect: () => {},
    });
    await click(".o_select_menu_toggler");
    await animationFrame();

    const input = queryOne(".o_select_menu_input");
    await click(input);
    await animationFrame();
    await press("ArrowDown");
    await animationFrame();

    expect(document.activeElement).toBe(input);
    const controlled = document.getElementById(input.getAttribute("aria-controls"));
    expect(controlled).toBe(queryOne("[role=listbox]"));
    expect(controlled).not.toBe(queryOne(".o_select_menu_menu"));

    const activeEl = document.getElementById(
        input.getAttribute("aria-activedescendant"),
    );
    expect(activeEl).not.toBe(null);
    expect(activeEl).toHaveClass("focus");
    expect(activeEl).toHaveAttribute("role", "option");
    expect(activeEl).toHaveAttribute("aria-selected", "true");
});

test("choices mutated in place are re-sorted on the next open", async () => {
    class InPlaceChoices extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`<SelectMenu choices="state.choices"/>`;
        setup() {
            this.state = useState({
                choices: [
                    { label: "Bravo", value: "b" },
                    { label: "Alpha", value: "a" },
                ],
            });
        }
    }
    const parent = await mountWithCleanup(InPlaceChoices);

    await contains(".o_select_menu_toggler").click();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Alpha", "Bravo"]);
    await contains(".o_select_menu_toggler").click();
    await animationFrame();

    parent.state.choices.push({ label: "Charlie", value: "c" });
    await animationFrame();

    await contains(".o_select_menu_toggler").click();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Alpha", "Bravo", "Charlie"]);
    await contains(".o_select_menu_toggler").click();
    await animationFrame();

    parent.state.choices.splice(0, 3, { label: "Zulu", value: "z" });
    await animationFrame();

    await contains(".o_select_menu_toggler").click();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Zulu"]);
});

test("the toggler picks up a value whose choice only arrives with the groups", async () => {
    class MyParent extends Component {
        static components = { SelectMenu };
        static props = ["*"];
        static template = xml`<SelectMenu groups="state.groups" value="state.value"/>`;
        setup() {
            this.state = useState({ groups: [], value: "optionB" });
        }
    }
    const parent = await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler_slot, .o_select_menu_toggler").toHaveCount(1);

    parent.state.groups = [
        { label: "Group A", choices: [{ label: "Option B", value: "optionB" }] },
    ];
    await animationFrame();

    expect(queryValue(".o_select_menu_toggler")).toBe("Option B");
});

test("a closed menu holds no rendered options", async () => {
    const choices = Array.from({ length: 80 }, (_, i) => ({
        label: `Option ${i}`,
        value: i,
    }));
    const menu = await mountSingleApp(SelectMenu, { choices, onSelect: () => {} });
    await contains(".o_select_menu_toggler").click();
    expect(menu.filtered.displayed.length).toBe(80);

    menu.dropdownState.close();
    await animationFrame();
    expect(menu.filtered.choices).toEqual([]);
    expect(menu.filtered.displayed).toEqual([]);
});

test("selected-value lookup does not scan the selection per choice", async () => {
    const CHOICES = 2000;
    const choices = [...Array(CHOICES)].map((_, i) => ({ value: i, label: `C${i}` }));
    const value = [...Array(100)].map((_, i) => CHOICES - 1 - i);

    let scanned = 0;
    const realIncludes = Array.prototype.includes;
    patchWithCleanup(Array.prototype, {
        includes(...args) {
            if (this === value) {
                scanned += this.length;
            }
            return realIncludes.apply(this, args);
        },
    });

    /** @type {Probe} */
    let menu;
    class Probe extends SelectMenu {
        setup() {
            super.setup();
            menu = this;
        }
    }
    class Parent extends Component {
        static components = { SelectMenu: Probe };
        static props = ["*"];
        static template = xml`<SelectMenu multiSelect="true" choices="choices" value="value"/>`;
        setup() {
            this.choices = choices;
            this.value = value;
        }
    }
    await mountWithCleanup(Parent);

    scanned = 0;
    menu.filterOptions("");
    for (const choice of menu.filtered.choices) {
        menu.getItemClass(choice);
    }
    expect(scanned).toBe(0);
});

test("the selected set follows a new value", async () => {
    const choices = [
        { value: "a", label: "A" },
        { value: "b", label: "B" },
    ];
    /** @type {Probe} */
    let menu;
    class Probe extends SelectMenu {
        setup() {
            super.setup();
            menu = this;
        }
    }
    class Parent extends Component {
        static components = { SelectMenu: Probe };
        static props = ["*"];
        static template = xml`<SelectMenu multiSelect="true" choices="choices" value="state.value"/>`;
        setup() {
            this.choices = choices;
            this.state = useState({ value: ["a"] });
        }
    }
    const parent = await mountWithCleanup(Parent);
    expect(menu.isOptionSelected(choices[0])).toBe(true);
    expect(menu.isOptionSelected(choices[1])).toBe(false);

    parent.state.value = ["b"];
    await animationFrame();
    expect(menu.isOptionSelected(choices[0])).toBe(false);
    expect(menu.isOptionSelected(choices[1])).toBe(true);
});

test("a selection mutated in place is still reflected", async () => {
    const choices = [
        { value: "a", label: "A" },
        { value: "b", label: "B" },
    ];
    /** @type {Probe} */
    let menu;
    class Probe extends SelectMenu {
        setup() {
            super.setup();
            menu = this;
        }
    }
    class Parent extends Component {
        static components = { SelectMenu: Probe };
        static props = ["*"];
        static template = xml`<SelectMenu multiSelect="true" choices="choices" value="state.value"/>`;
        setup() {
            this.choices = choices;
            this.state = useState({ value: ["a"] });
        }
    }
    const parent = await mountWithCleanup(Parent);
    expect(menu.isOptionSelected(choices[1])).toBe(false);

    parent.state.value.push("b");
    await animationFrame();
    expect(menu.isOptionSelected(choices[1])).toBe(true);

    parent.state.value.splice(0, 1);
    await animationFrame();
    expect(menu.isOptionSelected(choices[0])).toBe(false);
});

test("a choice replaced in place is reflected in the toggler", async () => {
    class MyParent extends Component {
        static components = { SelectMenu };
        static props = ["*"];
        static template = xml`<SelectMenu choices="state.choices" value="state.value" onSelect="() => {}"/>`;
        setup() {
            this.state = useState({
                value: "b",
                choices: [
                    { label: "Alpha", value: "a" },
                    { label: "Bee", value: "b" },
                ],
            });
        }
    }
    const parent = await mountSingleApp(MyParent);
    expect(".o_select_menu_toggler").toHaveValue("Bee");

    parent.state.choices.splice(1, 1, { label: "Bee v2", value: "b" });
    await animationFrame();
    expect(".o_select_menu_toggler").toHaveValue("Bee v2");
});

test("an open menu picks up choices pushed in place", async () => {
    class MyParent extends Component {
        static components = { SelectMenu };
        static props = ["*"];
        static template = xml`<SelectMenu choices="state.choices" value="state.value" onSelect="() => {}"/>`;
        setup() {
            this.state = useState({
                value: "b",
                choices: [
                    { label: "Alpha", value: "a" },
                    { label: "Bee", value: "b" },
                ],
            });
        }
    }
    const parent = await mountSingleApp(MyParent);
    await open();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Alpha", "Bee"]);

    parent.state.choices.push({ label: "Cee", value: "c" });
    await animationFrame();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Alpha", "Bee", "Cee"]);

    parent.state.choices.splice(0, 1);
    await animationFrame();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Bee", "Cee"]);
});

test("a multiSelect tag created in place shows up", async () => {
    class MyParent extends Component {
        static components = { SelectMenu };
        static props = ["*"];
        static template = xml`
            <SelectMenu choices="state.tags" value="state.tagIds" multiSelect="true"
                        onSelect="(values) => this.state.tagIds = values"/>
        `;
        setup() {
            this.state = useState({
                /** @type {{ value: any, label: string }[]} */
                tags: [{ value: 1, label: "Existing" }],
                /** @type {any[]} */
                tagIds: [1],
            });
        }
        createTag(/** @type {any} */ label) {
            this.state.tags.push({ value: "temp1", label });
            this.state.tagIds.push("temp1");
        }
    }
    const parent = await mountSingleApp(MyParent);
    expect(queryAllTexts(".o_tag")).toEqual(["Existing"]);

    parent.createTag("Brand new");
    await animationFrame();
    expect(queryAllTexts(".o_tag")).toEqual(["Existing", "Brand new"]);
});

test("a selected choice that leaves the choices keeps its label", async () => {
    class MyParent extends Component {
        static components = { SelectMenu };
        static props = ["*"];
        static template = xml`
            <SelectMenu choices="state.choices" value="state.value" multiSelect="true"
                        onSelect="() => {}"/>
        `;
        setup() {
            this.state = useState({
                value: ["a"],
                choices: [{ label: "Alpha", value: "a" }],
            });
        }
    }
    const parent = await mountSingleApp(MyParent);
    expect(queryAllTexts(".o_tag")).toEqual(["Alpha"]);

    parent.state.choices.splice(0, 1);
    await animationFrame();
    expect(queryAllTexts(".o_tag")).toEqual(["Alpha"]);
});

test("a choice renamed in place is re-sorted", async () => {
    class MyParent extends Component {
        static components = { SelectMenu };
        static props = ["*"];
        static template = xml`
            <SelectMenu choices="state.choices" value="'a'" onSelect="() => {}"/>
        `;
        setup() {
            this.state = useState({
                choices: [
                    { label: "Alpha", value: "a" },
                    { label: "Bravo", value: "b" },
                ],
            });
        }
    }
    const parent = await mountSingleApp(MyParent);
    await open();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Alpha", "Bravo"]);

    parent.state.choices[0].label = "Zulu";
    await animationFrame();

    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Bravo", "Zulu"]);
});

test("a choice renamed in place is re-matched against the live query", async () => {
    class MyParent extends Component {
        static components = { SelectMenu };
        static props = ["*"];
        static template = xml`
            <SelectMenu choices="state.choices" value="'a'" onSelect="() => {}"/>
        `;
        setup() {
            this.state = useState({
                choices: [
                    { label: "Alpha", value: "a" },
                    { label: "Bravo", value: "b" },
                ],
            });
        }
    }
    const parent = await mountSingleApp(MyParent);
    await open();
    await editInput("alp");
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Alpha"]);

    parent.state.choices[0].label = "Zulu";
    await animationFrame();

    expect(queryAllTexts(".o_select_menu_item")).toEqual([]);
});

test("a single-select listbox leaves aria-selected to the cursor", async () => {
    await mountSingleApp(Parent);
    await open();

    expect(`[role="listbox"]`).not.toHaveAttribute("aria-multiselectable");
    expect(queryOne(".o_select_menu_item.selected")).toHaveAttribute(
        "aria-selected",
        "false",
    );
});

test("a multiSelect listbox says so, and marks every picked choice", async () => {
    class MyParent extends Component {
        static components = { SelectMenu };
        static props = ["*"];
        static template = xml`
            <SelectMenu multiSelect="true" choices="choices" value="state.value"
                        onSelect="() => {}"/>
        `;
        setup() {
            this.state = useState({ value: ["hello", "moon"] });
            this.choices = [
                { label: "Hello", value: "hello" },
                { label: "World", value: "world" },
                { label: "Moon", value: "moon" },
            ];
        }
    }
    await mountSingleApp(MyParent);
    await open();

    expect(`[role="listbox"]`).toHaveAttribute("aria-multiselectable", "true");
    expect(
        queryAll(`[role="option"]`).map((o) => [
            o.textContent.trim(),
            o.getAttribute("aria-selected"),
        ]),
    ).toEqual([
        ["Hello", "true"],
        ["Moon", "true"],
        ["World", "false"],
    ]);
});

test.tags("mobile");
test("a bottom sheet has one combobox, and one holder of id and name", async () => {
    class MyParent extends Component {
        static components = { SelectMenu };
        static props = ["*"];
        static template = xml`
            <SelectMenu id="'sm-id'" name="'sm-name'" choices="choices"
                        value="'world'" onSelect="() => {}"/>
        `;
        setup() {
            this.choices = [{ label: "World", value: "world" }];
        }
    }
    await mountSingleApp(MyParent);
    await open();

    expect(`input`).toHaveCount(2);
    expect(`[role="combobox"]`).toHaveCount(1);
    expect(`[role="combobox"]`).toHaveClass("o_select_menu_input");
    expect(queryAll(`[id="sm-id"]`)).toHaveLength(1);
    expect(queryAll(`[name="sm-name"]`)).toHaveLength(1);
});

test("the listbox owns options and nothing else", async () => {
    /** @param {string} label */
    const rolesInListbox = (label) => {
        const listbox = queryOne("[role=listbox]");
        const roles = queryAll(":scope > *", { root: listbox }).map(
            (el) => el.getAttribute("role") || `<${el.tagName.toLowerCase()}>`,
        );
        return `${label}: ${[...new Set(roles)].sort().join(",")}`;
    };

    await mountSingleApp(SelectMenu, {
        choices: [
            { label: "Alpha", value: "a" },
            { label: "Beta", value: "b" },
        ],
        groups: [{ label: "Group", choices: [{ label: "Gamma", value: "c" }] }],
        searchable: true,
        onSelect: () => {},
    });
    await click(".o_select_menu_toggler");
    await animationFrame();
    expect(rolesInListbox("with choices")).toBe("with choices: option,presentation");

    expect("[role=listbox] input").toHaveCount(0);
});

test("the empty notice is a live region outside the listbox", async () => {
    await mountSingleApp(SelectMenu, {
        choices: [],
        searchable: true,
        onSelect: () => {},
    });
    await click(".o_select_menu_toggler");
    await animationFrame();

    expect("[role=status]").toHaveCount(1);
    expect("[role=status]").toHaveText("No results");
    expect("[role=listbox] [role=status]").toHaveCount(0);
    expect(queryAll(":scope > *", { root: queryOne("[role=listbox]") })).toHaveLength(
        0,
    );
});

test.tags("desktop");
test("the listbox wrapper is transparent to the menu's layout", async () => {
    await mountSingleApp(SelectMenu, {
        groups: [
            {
                label: "Group A",
                choices: Array.from({ length: 40 }, (_, i) => ({
                    label: `A${i}`,
                    value: `a${i}`,
                })),
            },
        ],
        searchable: true,
        onSelect: () => {},
    });
    await click(".o_select_menu_toggler");
    await animationFrame();

    const menu = queryOne(".o_select_menu_menu");
    const listbox = queryOne("[role=listbox]");
    expect(menu.scrollHeight).toBeGreaterThan(menu.clientHeight);
    expect(listbox.scrollHeight).toBe(listbox.clientHeight);

    expect(Math.round(listbox.getBoundingClientRect().width)).toBe(
        Math.round(menu.clientWidth),
    );

    const header = queryOne(".o_select_menu_group");
    const firstTop = queryAll(".o_select_menu_item")[0].getBoundingClientRect().top;
    menu.scrollTop = 200;
    await animationFrame();
    expect(menu.scrollTop).toBe(200);
    const menuTop = menu.getBoundingClientRect().top;
    expect(header.getBoundingClientRect().top - menuTop).toBeLessThan(4);
    expect(queryAll(".o_select_menu_item")[0].getBoundingClientRect().top).toBeLessThan(
        firstTop - 100,
    );
});

test("a menu that loses its search box moves real focus again", async () => {
    class Parent extends Component {
        static template = xml`<SelectMenu choices="choices" value="'a'" searchable="state.searchable"/>`;
        static components = { SelectMenu };
        static props = [];
        choices = [
            { value: "a", label: "Alpha" },
            { value: "b", label: "Beta" },
        ];
        state = useState({ searchable: true });
    }
    const parent = await mountWithCleanup(Parent);

    parent.state.searchable = false;
    await animationFrame();

    await contains(".o_select_menu_toggler").click();
    await animationFrame();
    await press("ArrowDown");
    await animationFrame();

    expect(document.activeElement).not.toBe(document.body);
    expect(document.activeElement).toHaveClass("o-dropdown-item");
});

test("the value index resolves across groups, first match winning", async () => {
    class Parent extends Component {
        static template = xml`<SelectMenu choices="choices" groups="groups" value="state.value"/>`;
        static components = { SelectMenu };
        static props = [];
        choices = [{ value: "a", label: "Alpha" }];
        groups = [
            { label: "Group", choices: [{ value: "b", label: "Beta" }] },
            { label: "Other", choices: [{ value: "b", label: "Beta again" }] },
        ];
        state = useState({ value: "a" });
    }
    const parent = await mountWithCleanup(Parent);
    expect(".o_select_menu_toggler").toHaveValue("Alpha");

    parent.state.value = "b";
    await animationFrame();
    expect(".o_select_menu_toggler").toHaveValue("Beta");
});

test("the value index is rebuilt when a label is edited in place", async () => {
    class Parent extends Component {
        static template = xml`<SelectMenu choices="state.choices" value="'a'"/>`;
        static components = { SelectMenu };
        static props = [];
        state = useState({
            choices: [
                { value: "a", label: "Alpha" },
                { value: "b", label: "Beta" },
            ],
        });
    }
    const parent = await mountWithCleanup(Parent);
    expect(".o_select_menu_toggler").toHaveValue("Alpha");

    parent.state.choices[0].label = "Renamed";
    await animationFrame();
    expect(".o_select_menu_toggler").toHaveValue("Renamed");
});

test("a selected tag survives its choice leaving the list", async () => {
    class Parent extends Component {
        static template = xml`<SelectMenu choices="state.choices" value="state.value" multiSelect="true"/>`;
        static components = { SelectMenu };
        static props = [];
        state = useState({
            choices: [
                { value: "a", label: "Alpha" },
                { value: "b", label: "Beta" },
            ],
            value: ["a", "b"],
        });
    }
    const parent = await mountWithCleanup(Parent);
    expect(queryAllTexts(".o_tag")).toEqual(["Alpha", "Beta"]);

    parent.state.choices = [{ value: "a", label: "Alpha" }];
    await animationFrame();
    expect(queryAllTexts(".o_tag")).toEqual(["Alpha", "Beta"]);

    parent.state.value = ["a"];
    await animationFrame();
    expect(queryAllTexts(".o_tag")).toEqual(["Alpha"]);
});

class MemoryParent extends Component {
    static template = xml`<SelectMenu choices="state.choices" value="state.value" onSelect.bind="onSelect"/>`;
    static components = { SelectMenu };
    static props = ["*"];
    setup() {
        this.state = useState({
            choices: this.props.initialChoices,
            value: this.props.initialValue,
        });
    }
    onSelect(value) {
        this.state.value = value;
    }
}

test.tags("desktop");
test("a real value whose choice leaves the list still shows its label", async () => {
    const parent = await mountWithCleanup(MemoryParent, {
        props: {
            initialChoices: [
                { value: "a", label: "Apple" },
                { value: "b", label: "Banana" },
            ],
            initialValue: "a",
        },
    });
    expect(".o_select_menu_toggler_slot, .o_select_menu_input").toHaveCount(1);
    expect(queryValue(".o_select_menu_input")).toBe("Apple");

    parent.state.choices = [{ value: "b", label: "Banana" }];
    await animationFrame();
    expect(queryValue(".o_select_menu_input")).toBe("Apple", {
        message: "the label survives its choice leaving the list",
    });
});

test.tags("desktop");
test("a cleared value does not inherit a label the list has stopped offering", async () => {
    const parent = await mountWithCleanup(MemoryParent, {
        props: {
            initialChoices: [
                { value: false, label: "View" },
                { value: 1, label: "Edit" },
            ],
            initialValue: false,
        },
    });
    expect(queryValue(".o_select_menu_input")).toBe("View");

    parent.state.choices = [{ value: 1, label: "Edit" }];
    await animationFrame();
    expect(queryValue(".o_select_menu_input")).toBe("", {
        message: "false is the empty scalar, not a remembered selection",
    });
});

test("new choices arriving while the menu is open are filtered in the render they trigger", async () => {
    let renders = 0;
    patchWithCleanup(SelectMenu.prototype, {
        setup() {
            super.setup();
            onWillRender(() => renders++);
        },
    });
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`<SelectMenu choices="state.choices" value="'a'"/>`;
        setup() {
            this.state = useState({ choices: [{ label: "A", value: "a" }] });
        }
    }
    const parent = await mountSingleApp(MyParent);
    await open();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["A"]);

    const opened = renders;
    parent.state.choices = [
        { label: "A", value: "a" },
        { label: "B", value: "b" },
    ];
    await animationFrame();
    await animationFrame();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["A", "B"]);
    expect(renders - opened).toBe(1, {
        message:
            "the props update is the render that filters; deriving the list costs none",
    });
});

test("typing into an open menu renders neither the menu nor its options until the debounced search", async () => {
    let menuRenders = 0;
    let popoverRenders = 0;
    patchWithCleanup(SelectMenu.prototype, {
        setup() {
            super.setup();
            onRendered(() => menuRenders++);
        },
    });
    patchWithCleanup(DropdownPopover.prototype, {
        setup() {
            super.setup();
            onRendered(() => popoverRenders++);
        },
    });
    class MyParent extends Component {
        static props = ["*"];
        static components = { SelectMenu };
        static template = xml`<SelectMenu choices="choices" value="'v1'"/>`;
        choices = [...Array(30)].map((_, i) => ({
            label: `Option ${i}`,
            value: `v${i}`,
        }));
    }
    await mountSingleApp(MyParent);
    await open();
    expect(".o_select_menu_item").toHaveCount(30);
    menuRenders = 0;
    popoverRenders = 0;

    await edit("Option 2", { confirm: false });
    await animationFrame();
    expect(menuRenders).toBe(0);
    expect(popoverRenders).toBe(0);
    expect("input.o_select_menu_input").toHaveValue("Option 2");
    expect(".o_select_menu_item").toHaveCount(30);

    await runAllTimers();
    await animationFrame();
    expect(menuRenders).toBe(1);
    expect(".o_select_menu_item").toHaveCount(12);
});

test("a disabled select menu cannot be opened through its caret", async () => {
    await mountWithCleanup(SelectMenu, {
        props: { choices: [{ value: 1, label: "One" }], disabled: true },
    });
    queryOne(".o_select_menu_caret").click();
    await animationFrame();
    expect(".o_select_menu_menu").toHaveCount(0);
});

test("a zero-valued selection displays its custom toggler instead of the placeholder", async () => {
    class Parent extends Component {
        static components = { SelectMenu };
        static props = ["*"];
        static template = xml`<SelectMenu choices="[{value: 0, label: 'Zero'}]" value="0" placeholder="'Choose'">Selected zero</SelectMenu>`;
    }
    await mountWithCleanup(Parent);
    expect(".o_select_menu_toggler_slot").toHaveText("Selected zero");
});
