import { expect, test } from "@odoo/hoot";
import {
    Deferred,
    animationFrame,
    hover,
    isInViewPort,
    isScrollable,
    pointerDown,
    pointerUp,
    press,
    queryAllAttributes,
    queryAllTexts,
    queryFirst,
    queryOne,
    queryRect,
    runAllTimers,
} from "@odoo/hoot-dom";
import { Component, useState, xml } from "@odoo/owl";

import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

/**
 * Helper needed until `isInViewPort` also checks intermediate parent elements.
 * This is to make sure an element is actually visible, not just "within
 * viewport boundaries" but below or above a parent's scroll point.
 *
 * @param {import("@odoo/hoot-dom").Target} target
 * @returns {boolean}
 */
function isInViewWithinScrollableY(target) {
    const element = queryFirst(target);
    let container = element.parentElement;
    while (
        container &&
        (container.scrollHeight <= container.clientHeight ||
            !["auto", "scroll"].includes(getComputedStyle(container).overflowY))
    ) {
        container = container.parentElement;
    }
    if (!container) {
        return isInViewPort(element);
    }
    const { x, y } = queryRect(element);
    const { height: containerHeight, width: containerWidth } = queryRect(container);
    return y > 0 && y < containerHeight && x > 0 && x < containerWidth;
}

function buildSources(generate, options = {}) {
    return [
        {
            options: generate,
            optionSlot: options.optionSlot,
        },
    ];
}

function item(label, onSelect, data = {}) {
    return {
        data,
        label,
        onSelect() {
            return onSelect?.(this);
        },
    };
}

test("can be rendered", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`<AutoComplete value="'Hello'" sources="sources"/>`;
        static props = [];

        sources = buildSources(() => [item("World"), item("Hello")]);
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
        static template = xml`<AutoComplete value="state.value" sources="sources"/>`;
        static props = [];

        state = useState({ value: "Hello" });
        sources = buildSources(() => [
            item("World", this.onSelect.bind(this)),
            item("Hello", this.onSelect.bind(this)),
        ]);

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
                <AutoComplete value="''" sources="sources" resetOnSelect="true"/>
            </div>
        `;
        static props = [];

        state = useState({ value: "Hello" });
        sources = buildSources(() => [
            item("World", this.onSelect.bind(this)),
            item("Hello", this.onSelect.bind(this)),
        ]);

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
        static template = xml`<AutoComplete value="'Hello'" sources="sources"/>`;
        static props = [];

        sources = buildSources(() => [item("World"), item("Hello")]);
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
        static template = xml`<AutoComplete value="'Hello'" sources="sources" autoSelect="true"/>`;
        static props = [];

        sources = buildSources(() => [item("World"), item("Hello")]);
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
        static template = xml`<AutoComplete value="'Bar'" sources="sources"/>`;
        static props = [];

        sources = buildSources(() => [item("Bar")]);
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
                    <AutoComplete value="'Hello'" sources="sources" autoSelect="true"/>
                </div>
            </div>
        `;
        static props = [];

        sources = buildSources(() => [item("World"), item("Hello")]);
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
                    <AutoComplete value="'Hello'" sources="sources"/>
                </div>
            </div>
        `;
        static props = [];

        sources = buildSources(() => [item("World"), item("Hello")]);
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
        static template = xml`<AutoComplete value="'Hello'" sources="sources" autoSelect="true"/>`;
        static props = [];

        sources = buildSources(() => [item("World"), item("Hello")]);
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
        static template = xml`<AutoComplete value="'Hello'" sources="sources"/>`;
        static props = [];

        sources = buildSources(() => [item("World"), item("Hello")]);
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
    const ITEMS = [item("AB"), item("AC"), item("BC")];

    let def = new Deferred();
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`<AutoComplete value="''" sources="sources"/>`;
        static props = [];

        sources = buildSources(async (request) => {
            await def;
            return ITEMS.filter((option) => option.label.includes(request));
        });
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
        static template = xml`<AutoComplete value="''" sources="sources"/>`;
        static props = [];

        sources = buildSources(() => []);
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
        static template = xml`<AutoComplete value="''" sources="sources"/>`;
        static props = [];

        sources = buildSources((request) =>
            request.length > 2 ? [item("test A"), item("test B"), item("test C")] : []
        );
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

test.tags("desktop");
test("autofocus=true option work as expected", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`<AutoComplete value="'Hello'" sources="sources" autofocus="true"/>`;
        static props = [];

        sources = buildSources(() => [item("World"), item("Hello")]);
    }

    await mountWithCleanup(Parent);
    expect(".o-autocomplete input").toBeFocused();
});

test.tags("desktop");
test("autocomplete in edition keep edited value before select option", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <button class="myButton" t-on-mouseover="onHover">My button</button>
            <AutoComplete value="this.state.value" sources="sources"/>
        `;
        static props = [];

        sources = buildSources(() => [item("My Selection", this.onSelect.bind(this))]);
        state = useState({ value: "Hello" });

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

test.tags("desktop");
test("autocomplete in edition keep edited value before blur", async () => {
    let count = 0;
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <button class="myButton" t-on-mouseover="onHover">My button</button>
            <AutoComplete value="this.state.value" sources="[]"/>
        `;
        static props = [];

        state = useState({ value: "Hello" });

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
                onBlur.bind="onBlur"
                onChange.bind="onChange"
                autoSelect="true"
            />
        `;
        static props = [];

        state = useState({ value: "" });
        sources = buildSources(() => [
            item("World", this.onSelect.bind(this)),
            item("Hello", this.onSelect.bind(this)),
        ]);

        onBlur() {
            expect.step("blur");
        }
        onChange() {
            expect.step("change");
        }
        onSelect(option) {
            this.state.value = option.label;
            expect.step(`select ${option.label}`);
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
        static template = xml`<AutoComplete value="state.value" sources="sources" autoSelect="true"/>`;
        static components = { AutoComplete };
        static props = [];

        state = useState({ value: "" });
        sources = buildSources(() => [
            item("World", this.onSelect.bind(this)),
            item("Hello", this.onSelect.bind(this)),
        ]);

        onSelect(option) {
            this.state.value = option.label;
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

test("autocomplete trim spaces for search", async () => {
    const ITEMS = [item("World"), item("Hello")];

    class Parent extends Component {
        static template = xml`<AutoComplete value="state.value" sources="sources"/>`;
        static components = { AutoComplete };
        static props = [];

        state = useState({ value: " World" });
        sources = buildSources((request) => ITEMS.filter(({ label }) => label.startsWith(request)));
    }
    await mountWithCleanup(Parent);
    await contains(`.o-autocomplete input`).click();
    expect(queryAllTexts(`.o-autocomplete--dropdown-item`)).toEqual(["World", "Hello"]);
});

test("tab and shift+tab close the dropdown", async () => {
    class Parent extends Component {
        static template = xml`<AutoComplete value="state.value" sources="sources"/>`;
        static components = { AutoComplete };
        static props = [];

        state = useState({ value: "" });
        sources = buildSources(() => [item("World"), item("Hello")]);
    }
    await mountWithCleanup(Parent);
    const input = ".o-autocomplete input";
    const dropdown = ".o-autocomplete--dropdown-menu";
    expect(input).toHaveCount(1);
    // Tab
    await contains(input).click();
    expect(dropdown).toBeVisible();
    await press("Tab");
    await animationFrame();
    expect(dropdown).not.toHaveCount();
    // Shift + Tab
    await contains(input).click();
    expect(dropdown).toBeVisible();
    await press("Tab", { shiftKey: true });
    await animationFrame();
    expect(dropdown).not.toHaveCount();
});

test("Clicking away selects the first option when selectOnBlur is true", async () => {
    class Parent extends Component {
        static template = xml`<AutoComplete value="state.value" sources="sources" selectOnBlur="true"/>`;
        static components = { AutoComplete };
        static props = [];

        state = useState({ value: "" });
        sources = buildSources(() => [
            item("World", this.onSelect.bind(this)),
            item("Hello", this.onSelect.bind(this)),
        ]);

        onSelect(option) {
            this.state.value = option.label;
            expect.step(option.label);
        }
    }

    await mountWithCleanup(Parent);
    const input = ".o-autocomplete input";
    await contains(input).click();
    expect(".o-autocomplete--dropdown-menu").toBeVisible();
    queryFirst(input).blur();
    await animationFrame();
    expect(input).toHaveValue("World");
    expect.verifySteps(["World"]);
});

test("selectOnBlur doesn't interfere with selecting by mouse clicking", async () => {
    class Parent extends Component {
        static template = xml`<AutoComplete value="state.value" sources="sources" selectOnBlur="true"/>`;
        static components = { AutoComplete };
        static props = [];

        state = useState({ value: "" });
        sources = buildSources(() => [
            item("World", this.onSelect.bind(this)),
            item("Hello", this.onSelect.bind(this)),
        ]);

        onSelect(option) {
            this.state.value = option.label;
            expect.step(option.label);
        }
    }

    await mountWithCleanup(Parent);
    const input = ".o-autocomplete input";
    await contains(input).click();
    await contains(".o-autocomplete--dropdown-item:last").click();
    expect(input).toHaveValue("Hello");
    expect.verifySteps(["Hello"]);
});

test("autocomplete scrolls when moving with arrows", async () => {
    class Parent extends Component {
        static template = xml`
            <style>
                .o-autocomplete--dropdown-menu {
                    max-height: 100px;
                }
            </style>
            <AutoComplete value="state.value" sources="sources" autoSelect="true"/>
        `;
        static components = { AutoComplete };
        static props = [];

        state = useState({ value: "" });
        sources = buildSources(() => [
            item("Never"),
            item("Gonna"),
            item("Give"),
            item("You"),
            item("Up"),
        ]);
    }
    const dropdownSelector = ".o-autocomplete--dropdown-menu";
    const activeItemSelector = ".o-autocomplete--dropdown-item .ui-state-active";
    const msgInView = "active item should be in view within dropdown";
    const msgNotInView = "item should not be in view within dropdown";
    await mountWithCleanup(Parent);
    expect(".o-autocomplete input").toHaveCount(1);
    // Open with arrow key.
    await contains(".o-autocomplete input").focus();
    await press("ArrowDown");
    await animationFrame();
    expect(".o-autocomplete--dropdown-item").toHaveCount(5);
    expect(isScrollable(dropdownSelector)).toBe(true, { message: "dropdown should be scrollable" });
    // First element focused and visible (dropdown is not scrolled yet).
    expect(".o-autocomplete--dropdown-item:first-child a").toHaveClass("ui-state-active");
    expect(isInViewWithinScrollableY(activeItemSelector)).toBe(true, { message: msgInView });
    // Navigate with the arrow keys. Go to the last item.
    expect(isInViewWithinScrollableY(".o-autocomplete--dropdown-item:contains('Up')")).toBe(false, {
        message: "'Up' " + msgNotInView,
    });
    await press("ArrowUp");
    await press("ArrowUp");
    await animationFrame();
    expect(activeItemSelector).toHaveText("Up");
    expect(isInViewWithinScrollableY(activeItemSelector)).toBe(true, { message: msgInView });
    // Navigate to an item that is not currently visible.
    expect(isInViewWithinScrollableY(".o-autocomplete--dropdown-item:contains('Never')")).toBe(
        false,
        { message: "'Never' " + msgNotInView }
    );
    for (let i = 0; i < 4; i++) {
        await press("ArrowUp");
    }
    await animationFrame();
    expect(activeItemSelector).toHaveText("Never");
    expect(isInViewWithinScrollableY(activeItemSelector)).toBe(true, { message: msgInView });
    expect(isInViewWithinScrollableY(".o-autocomplete--dropdown-item:last")).toBe(false, {
        message: "last " + msgNotInView,
    });
});

test("source with option slot", async () => {
    class Parent extends Component {
        static template = xml`
            <AutoComplete value="''" sources="sources">
                <t t-set-slot="use_this_slot" t-slot-scope="scope">
                    <div class="slot_item">
                        <t t-esc="scope.data.id"/>: <t t-esc="scope.label"/>
                    </div>
                </t>
            </AutoComplete>
        `;
        static components = { AutoComplete };
        static props = [];

        sources = buildSources(
            () => [item("Hello", () => {}, { id: 1 }), item("World", () => {}, { id: 2 })],
            { optionSlot: "use_this_slot" }
        );
    }

    await mountWithCleanup(Parent);
    await contains(`.o-autocomplete input`).click();
    expect(queryAllTexts(`.o-autocomplete--dropdown-item .slot_item`)).toEqual([
        "1: Hello",
        "2: World",
    ]);
});

test("unselectable options are... not selectable", async () => {
    class Parent extends Component {
        static template = xml`
            <AutoComplete value="''" sources="sources"/>
        `;
        static components = { AutoComplete };
        static props = [];

        sources = buildSources(() => [
            { label: "unselectable" },
            item("selectable", this.onSelect.bind(this)),
            { label: "selectable" },
            { label: "unselectable" },
        ]);

        onSelect(option) {
            expect.step(`selected: ${option.label}`);
        }
    }

    await mountWithCleanup(Parent);
    await contains(`.o-autocomplete input`).click();
    expect(`.o-autocomplete--input`).toHaveAttribute("aria-activedescendant", "autocomplete_0_1");
    expect(`.dropdown-item#autocomplete_0_1`).toHaveText("selectable");
    expect(`.dropdown-item#autocomplete_0_1`).toHaveAttribute("aria-selected", "true");

    await press("arrowup");
    await animationFrame();
    expect(`.o-autocomplete--input`).not.toHaveAttribute("aria-activedescendant");

    await press("arrowdown");
    await animationFrame();
    expect(`.o-autocomplete--input`).toHaveAttribute("aria-activedescendant", "autocomplete_0_1");

    await press("arrowdown");
    await animationFrame();
    expect(`.o-autocomplete--input`).not.toHaveAttribute("aria-activedescendant");

    await press("arrowup");
    await animationFrame();
    expect(`.o-autocomplete--input`).toHaveAttribute("aria-activedescendant", "autocomplete_0_1");

    expect(`.o-autocomplete--input`).toBeFocused();
    await contains(`.dropdown-item:eq(0)`).click();
    expect(`.o-autocomplete--input`).toBeFocused();
    expect.verifySteps([]);

    await contains(`.dropdown-item:eq(2)`).click();
    expect(`.o-autocomplete--input`).toBeFocused();
    expect.verifySteps([]);

    await contains(`.dropdown-item:eq(1)`).click();
    expect(`.o-autocomplete--input`).toBeFocused();
    expect.verifySteps(["selected: selectable"]);
});

test.tags("desktop");
test("items are selected only when the mouse moves, not just on enter", async () => {
    class Parent extends Component {
        static template = xml`<AutoComplete value="''" sources="sources"/>`;
        static components = { AutoComplete };
        static props = [];

        sources = buildSources(() => [item("one"), item("two"), item("three")]);
    }

    // In this test we use custom events to prevent unwanted mouseenter/mousemove events

    await mountWithCleanup(Parent);
    queryOne(`.o-autocomplete input`).focus();
    queryOne(`.o-autocomplete input`).click();
    await animationFrame();

    expect(".o-autocomplete--dropdown-item:nth-child(1) .dropdown-item").toHaveClass(
        "ui-state-active"
    );

    await hover(".o-autocomplete--dropdown-item:nth-child(2)");
    await animationFrame();
    // mouseenter should be ignored
    expect(".o-autocomplete--dropdown-item:nth-child(2) .dropdown-item").not.toHaveClass(
        "ui-state-active"
    );

    await press("arrowdown");
    await animationFrame();
    expect(".o-autocomplete--dropdown-item:nth-child(2) .dropdown-item").toHaveClass(
        "ui-state-active"
    );

    await hover(".o-autocomplete--dropdown-item:nth-child(3)");
    await animationFrame();
    expect(".o-autocomplete--dropdown-item:nth-child(2) .dropdown-item").not.toHaveClass(
        "ui-state-active"
    );
    expect(".o-autocomplete--dropdown-item:nth-child(3) .dropdown-item").toHaveClass(
        "ui-state-active"
    );
});
