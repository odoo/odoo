import { expect, test } from "@odoo/hoot";
import {
    pointerDown,
    pointerUp,
    queryAllAttributes,
    queryAllTexts,
    queryFirst,
    queryOne,
} from "@odoo/hoot-dom";
import { Deferred, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";

import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

test("can be rendered", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <AutoComplete
                value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                onSelect="() => {}"
            />
        `;
        static props = {};
    }

    await mountWithCleanup(Parent);
    expect(".o-autocomplete").toHaveCount(1);
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);

    await contains(".o-autocomplete input").click();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
    expect(queryAllTexts(".o-autocomplete--dropdown-item")).toEqual(["World", "Hello"]);

    const dropdownItemIds = queryAllAttributes(".dropdown-item", "id");
    expect(dropdownItemIds).toEqual(["autocomplete_0_0", "autocomplete_0_1"]);
    expect(queryAllAttributes(".dropdown-item", "role")).toEqual(["option", "option"]);
    expect(queryAllAttributes(".dropdown-item", "aria-selected")).toEqual(["true", "false"]);
    expect(".o-autocomplete--input").toHaveAttribute("aria-activedescendant", dropdownItemIds[0]);
});

test("select option", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <AutoComplete
                value="state.value"
                sources="sources"
                onSelect="(option) => this.onSelect(option)"
            />
        `;
        static props = {};
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
            expect.step(option.label);
        }
    }

    await mountWithCleanup(Parent);
    expect(".o-autocomplete input").toHaveValue("Hello");

    await contains(".o-autocomplete input").click();
    await contains(queryFirst(".o-autocomplete--dropdown-item")).click();
    expect(".o-autocomplete input").toHaveValue("World");
    expect.verifySteps(["World"]);

    await contains(".o-autocomplete input").click();
    await contains(".o-autocomplete--dropdown-item:last").click();
    expect(".o-autocomplete input").toHaveValue("Hello");
    expect.verifySteps(["Hello"]);
});

test("autocomplete with resetOnSelect='true'", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
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
        static props = {};
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
            expect.step(option.label);
        }
    }

    await mountWithCleanup(Parent);
    expect(".test_value").toHaveText("Hello");
    expect(".o-autocomplete input").toHaveValue("");

    await contains(".o-autocomplete input").edit("Blip", { confirm: false });
    await runAllTimers();
    await contains(".o-autocomplete--dropdown-item:last").click();
    expect(".test_value").toHaveText("Hello");
    expect(".o-autocomplete input").toHaveValue("");
    expect.verifySteps(["Hello"]);
});

test("open dropdown on input", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <AutoComplete
                value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                onSelect="() => {}"
            />
        `;
        static props = {};
    }

    await mountWithCleanup(Parent);

    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
    await contains(".o-autocomplete input").fill("a", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
});

test("cancel result on escape keydown", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <AutoComplete
                value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                onSelect="() => {}"
                autoSelect="true"
            />
        `;
        static props = {};
    }

    await mountWithCleanup(Parent);
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
    expect(".o-autocomplete input").toHaveValue("Hello");

    await contains(".o-autocomplete input").click();
    await contains(".o-autocomplete input").edit("H", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);

    await contains(".o-autocomplete input").press("Escape");
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
    expect(".o-autocomplete input").toHaveValue("Hello");
});

test("select input text on first focus", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <AutoComplete value="'Bar'" sources="[{ options: [{ label: 'Bar' }] }]" onSelect="() => {}"/>
        `;
        static props = {};
    }

    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").click();
    await runAllTimers();
    expect(getSelection().toString()).toBe("Bar");
});

test("scroll outside should cancel result", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <div class="autocomplete_container overflow-auto" style="max-height: 100px;">
                <div style="height: 1000px;">
                    <AutoComplete
                        value="'Hello'"
                        sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                        onSelect="() => {}"
                        autoSelect="true"
                    />
                </div>
            </div>
        `;
        static props = {};
    }

    await mountWithCleanup(Parent);
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
    expect(".o-autocomplete input").toHaveValue("Hello");

    await contains(".o-autocomplete input").click();
    await contains(".o-autocomplete input").edit("H", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);

    await contains(".autocomplete_container").scroll({ top: 10 });
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
    expect(".o-autocomplete input").toHaveValue("Hello");
});

test("scroll inside should keep dropdown open", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <div class="autocomplete_container overflow-auto" style="max-height: 100px;">
                <div style="height: 1000px;">
                    <AutoComplete
                        value="'Hello'"
                        sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                        onSelect="() => {}"
                    />
                </div>
            </div>
        `;
        static props = {};
    }

    await mountWithCleanup(Parent);
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);

    await contains(".o-autocomplete input").click();
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);

    await contains(".o-autocomplete .dropdown-menu").scroll({ top: 10 });
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
});

test("losing focus should cancel result", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <AutoComplete
                value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                onSelect="() => {}"
                autoSelect="true"
            />
        `;
        static props = {};
    }

    await mountWithCleanup(Parent);
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
    expect(".o-autocomplete input").toHaveValue("Hello");

    await contains(".o-autocomplete input").click();
    await contains(".o-autocomplete input").edit("H", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);

    await contains(document.body).click();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
    expect(".o-autocomplete input").toHaveValue("Hello");
});

test("click out after clearing input", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <AutoComplete
                value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                onSelect="() => {}"
            />
        `;
        static props = {};
    }

    await mountWithCleanup(Parent);
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
    expect(".o-autocomplete input").toHaveValue("Hello");

    await contains(".o-autocomplete input").click();
    await contains(".o-autocomplete input").clear({ confirm: false });
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);

    await contains(document.body).click();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
    expect(".o-autocomplete input").toHaveValue("");
});

test("open twice should not display previous results", async () => {
    let def = new Deferred();
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <AutoComplete value="''" sources="sources" onSelect="() => {}"/>
        `;
        static props = {};
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

    await mountWithCleanup(Parent);
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);

    await contains(".o-autocomplete input").click();
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
    expect(".o-autocomplete--dropdown-item").toHaveCount(1);
    expect(".o-autocomplete--dropdown-item .fa-spin").toHaveCount(1); // loading

    def.resolve();
    await animationFrame();
    expect(".o-autocomplete--dropdown-item").toHaveCount(3);
    expect(".fa-spin").toHaveCount(0);

    def = new Deferred();
    await contains(".o-autocomplete input").fill("A", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete--dropdown-item").toHaveCount(1);
    expect(".o-autocomplete--dropdown-item .fa-spin").toHaveCount(1); // loading
    def.resolve();
    await runAllTimers();
    expect(".o-autocomplete--dropdown-item").toHaveCount(2);
    expect(".fa-spin").toHaveCount(0);

    await contains(queryFirst(".o-autocomplete--dropdown-item")).click();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);

    // re-open the dropdown -> should not display the previous results
    def = new Deferred();
    await contains(".o-autocomplete input").click();
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
    expect(".o-autocomplete--dropdown-item").toHaveCount(1);
    expect(".o-autocomplete--dropdown-item .fa-spin").toHaveCount(1); // loading
});

test("press enter on autocomplete with empty source", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`<AutoComplete value="''" sources="sources" onSelect="onSelect"/>`;
        static props = {};
        get sources() {
            return [{ options: [] }];
        }
        onSelect() {}
    }

    await mountWithCleanup(Parent);
    expect(".o-autocomplete input").toHaveCount(1);
    expect(".o-autocomplete input").toHaveValue("");
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);

    // click inside the input and press "enter", because why not
    await contains(".o-autocomplete input").click();
    await runAllTimers();
    await contains(".o-autocomplete input").press("Enter");

    expect(".o-autocomplete input").toHaveCount(1);
    expect(".o-autocomplete input").toHaveValue("");
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
});

test("press enter on autocomplete with empty source (2)", async () => {
    // in this test, the source isn't empty at some point, but becomes empty as the user
    // updates the input's value.
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`<AutoComplete value="''" sources="sources" onSelect="onSelect"/>`;
        static props = {};
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

    await mountWithCleanup(Parent);
    expect(".o-autocomplete input").toHaveCount(1);
    expect(".o-autocomplete input").toHaveValue("");

    await contains(".o-autocomplete input").edit("test", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
    expect(".o-autocomplete .dropdown-menu .o-autocomplete--dropdown-item").toHaveCount(3);

    await contains(".o-autocomplete input").edit("t", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);

    await contains(".o-autocomplete input").press("Enter");
    expect(".o-autocomplete input").toHaveCount(1);
    expect(".o-autocomplete input").toHaveValue("t");
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
});

test.tags("desktop")("autofocus=true option work as expected", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <AutoComplete value="'Hello'"
                sources="[{ options: [{ label: 'World' }, { label: 'Hello' }] }]"
                autofocus="true"
                onSelect="() => {}"
            />
        `;
        static props = {};
    }

    await mountWithCleanup(Parent);

    expect(".o-autocomplete input").toBeFocused();
});

test.tags("desktop")("autocomplete in edition keep edited value before select option", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <button class="myButton" t-on-mouseover="onHover">My button</button>
            <AutoComplete value="this.state.value"
            sources="[{ options: [{ label: 'My Selection' }] }]"
            onSelect.bind="onSelect"
            />
        `;
        static props = {};
        setup() {
            this.state = useState({ value: "Hello" });
        }

        onHover() {
            this.state.value = "My Click";
        }

        onSelect() {
            this.state.value = "My Selection";
        }
    }

    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").edit("Yolo", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete input").toHaveValue("Yolo");

    // We want to simulate an external value edition (like a delayed onChange)
    await contains(".myButton").hover();
    expect(".o-autocomplete input").toHaveValue("Yolo");

    // Leave inEdition mode when selecting an option
    await contains(".o-autocomplete input").click();
    await runAllTimers();
    await contains(queryFirst(".o-autocomplete--dropdown-item")).click();
    expect(".o-autocomplete input").toHaveValue("My Selection");

    // Will also trigger the hover event
    await contains(".myButton").click();
    expect(".o-autocomplete input").toHaveValue("My Click");
});

test.tags("desktop")("autocomplete in edition keep edited value before blur", async () => {
    let count = 0;
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <button class="myButton" t-on-mouseover="onHover">My button</button>
            <AutoComplete value="this.state.value"
            sources="[]"
            onSelect="() => {}"
            />
        `;
        static props = {};
        setup() {
            this.state = useState({ value: "Hello" });
        }

        onHover() {
            this.state.value = `My Click ${count++}`;
        }
    }

    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").edit("", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete input").toHaveValue("");

    // We want to simulate an external value edition (like a delayed onChange)
    await contains(".myButton").hover();
    expect(".o-autocomplete input").toHaveValue("");

    // Leave inEdition mode when blur the input
    await contains(document.body).click();
    expect(".o-autocomplete input").toHaveValue("");

    // Will also trigger the hover event
    await contains(".myButton").click();
    expect(".o-autocomplete input").toHaveValue("My Click 1");
});

test("correct sequence of blur, focus and select", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <AutoComplete
                value="state.value"
                sources="sources"
                onSelect.bind="onSelect"
                onBlur.bind="onBlur"
                onChange.bind="onChange"
                autoSelect="true"
            />
        `;
        static props = {};
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
            expect.step("change");
        }
        onSelect(option, params) {
            queryOne(".o-autocomplete input").value = option.label;
            expect.step("select " + option.label);
            expect(params.triggeredOnBlur).not.toBe(true);
        }
        onBlur() {
            expect.step("blur");
        }
    }
    await mountWithCleanup(Parent);
    expect(".o-autocomplete input").toHaveCount(1);
    await contains(".o-autocomplete input").click();

    // Navigate suggestions using arrow keys
    let dropdownItemIds = queryAllAttributes(".dropdown-item", "id");
    expect(dropdownItemIds).toEqual(["autocomplete_0_0", "autocomplete_0_1"]);
    expect(queryAllAttributes(".dropdown-item", "role")).toEqual(["option", "option"]);
    expect(queryAllAttributes(".dropdown-item", "aria-selected")).toEqual(["true", "false"]);
    expect(".o-autocomplete--input").toHaveAttribute("aria-activedescendant", dropdownItemIds[0]);

    await contains(".o-autocomplete--input").press("ArrowDown");

    dropdownItemIds = queryAllAttributes(".dropdown-item", "id");
    expect(dropdownItemIds).toEqual(["autocomplete_0_0", "autocomplete_0_1"]);
    expect(queryAllAttributes(".dropdown-item", "role")).toEqual(["option", "option"]);
    expect(queryAllAttributes(".dropdown-item", "aria-selected")).toEqual(["false", "true"]);
    expect(".o-autocomplete--input").toHaveAttribute("aria-activedescendant", dropdownItemIds[1]);

    // Start typing hello and click on the result
    await contains(".o-autocomplete input").edit("h", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
    await contains(".o-autocomplete--dropdown-item:last").click();
    expect.verifySteps(["change", "select Hello"]);
    expect(".o-autocomplete input").toBeFocused();

    // Clear input and focus out
    await contains(".o-autocomplete input").edit("", { confirm: false });
    await runAllTimers();
    await contains(document.body).click();
    expect.verifySteps(["blur", "change"]);
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
});

test("autocomplete always closes on click away", async () => {
    class Parent extends Component {
        static template = xml`
            <AutoComplete
                value="state.value"
                sources="sources"
                onSelect.bind="onSelect"
                autoSelect="true"
            />
        `;
        static props = ["*"];
        static components = { AutoComplete };
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
            queryOne(".o-autocomplete--input").value = option.label;
        }
    }
    await mountWithCleanup(Parent);
    expect(".o-autocomplete input").toHaveCount(1);
    await contains(".o-autocomplete input").click();
    expect(".o-autocomplete--dropdown-item").toHaveCount(2);
    await pointerDown(".o-autocomplete--dropdown-item:last");
    await pointerUp(document.body);
    expect(".o-autocomplete--dropdown-item").toHaveCount(2);
    await contains(document.body).click();
    expect(".o-autocomplete--dropdown-item").toHaveCount(0);
});
