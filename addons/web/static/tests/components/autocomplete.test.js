// @ts-check

import { expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    Deferred,
    edit,
    hover,
    isInViewPort,
    isScrollable,
    pointerDown,
    pointerUp,
    press,
    queryAll,
    queryAllAttributes,
    queryAllTexts,
    queryFirst,
    queryOne,
    queryRect,
    runAllTimers,
} from "@odoo/hoot-dom";
import { Component, onRendered, useState, xml } from "@odoo/owl";
import {
    contains,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { AutoComplete } from "@web/components/autocomplete/autocomplete";

/**
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

function buildSources(
    /** @type {any} */ generate,
    /** @type {{ optionSlot?: any }} */ options = {},
) {
    return [
        {
            options: generate,
            optionSlot: options.optionSlot,
        },
    ];
}

function item(
    /** @type {any} */ label,
    /** @type {any} */ onSelect = undefined,
    data = {},
) {
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
    expect(dropdownItemIds).toHaveLength(2);
    expect(dropdownItemIds[0]).toMatch(/_0_0$/);
    expect(dropdownItemIds[1]).toMatch(/_0_1$/);
    expect(queryAllAttributes(".dropdown-item", "role")).toEqual(["option", "option"]);
    expect(queryAllAttributes(".dropdown-item", "aria-selected")).toEqual([
        "true",
        "false",
    ]);
    expect(".o-autocomplete--input").toHaveAttribute(
        "aria-activedescendant",
        dropdownItemIds[0],
    );
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

        onSelect(/** @type {any} */ option) {
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

        onSelect(/** @type {any} */ option) {
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

test("pending debounced input is cancelled on close (no reopen after escape)", async () => {
    let loadCount = 0;
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`<AutoComplete value="'Hello'" sources="sources"/>`;
        static props = [];
        sources = buildSources(() => {
            loadCount++;
            return [item("World"), item("Hello")];
        });
    }

    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").click();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
    const loadsAfterOpen = loadCount;

    await contains(".o-autocomplete input").edit("Wor", { confirm: false });
    await contains(".o-autocomplete input").press("Escape");
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);

    await runAllTimers();
    await animationFrame();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
    expect(loadCount).toBe(loadsAfterOpen);
});

test("clicking the input while typing is pending still searches what was typed", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`<AutoComplete value="''" sources="sources"/>`;
        static props = [];
        sources = buildSources((/** @type {string} */ request) =>
            [item("World"), item("Hello")].filter((option) =>
                option.label.startsWith(request),
            ),
        );
    }

    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").click();
    expect(queryAllTexts(".o-autocomplete--dropdown-item")).toEqual(["World", "Hello"]);

    await contains(".o-autocomplete input").edit("Wor", { confirm: false });
    await contains(".o-autocomplete input").click();
    await runAllTimers();
    await animationFrame();
    expect(queryAllTexts(".o-autocomplete--dropdown-item")).toEqual(["World"]);
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

test("a scroll that did not move the input does not cancel the result", async () => {
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
    await contains(".o-autocomplete input").click();
    await contains(".o-autocomplete input").edit("H", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);

    queryOne(".autocomplete_container").dispatchEvent(new Event("scroll"));
    await animationFrame();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
    expect(".o-autocomplete input").toHaveValue("H");
});

test("arrow navigation does not scroll an ancestor of the fixed menu", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static props = [];
        static template = xml`
            <div class="autocomplete_container overflow-auto" style="height: 60px;">
                <div style="height: 1000px;">
                    <AutoComplete sources="sources"/>
                </div>
            </div>`;
        sources = buildSources(() => [
            item("First"),
            item("Second", () => expect.step("Second")),
        ]);
    }
    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").focus();
    await press("ArrowDown");
    await animationFrame();
    await press("ArrowDown");
    await animationFrame();
    expect(".autocomplete_container").toHaveProperty("scrollTop", 0);
    expect(".o-autocomplete--dropdown-menu").toHaveCount(1);
    expect(".ui-state-active").toHaveText("Second");
    await press("Enter");
    await animationFrame();
    expect.verifySteps(["Second"]);
});

test("a page-level scroll does not cancel the result", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <div class="autocomplete_container">
                <AutoComplete value="'Hello'" sources="sources" autoSelect="true"/>
            </div>
        `;
        static props = [];

        sources = buildSources(() => [item("World"), item("Hello")]);
    }

    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").click();
    await contains(".o-autocomplete input").edit("H", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);

    document.dispatchEvent(new Event("scroll"));
    await animationFrame();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
    expect(".o-autocomplete input").toHaveValue("H");
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

        sources = buildSources(async (/** @type {any} */ request) => {
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
    expect(".o-autocomplete--dropdown-item .fa-spin").toHaveCount(1);

    def.resolve();
    await animationFrame();
    expect(".o-autocomplete--dropdown-item").toHaveCount(3);
    expect(".fa-spin").toHaveCount(0);

    def = new Deferred();
    await contains(".o-autocomplete input").fill("A", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete--dropdown-item").toHaveCount(1);
    expect(".o-autocomplete--dropdown-item .fa-spin").toHaveCount(1);
    def.resolve();
    await animationFrame();
    expect(".o-autocomplete--dropdown-item").toHaveCount(2);
    expect(".fa-spin").toHaveCount(0);

    await contains(queryFirst(".o-autocomplete--dropdown-item")).click();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);

    def = new Deferred();
    await contains(".o-autocomplete input").click();
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
    expect(".o-autocomplete--dropdown-item").toHaveCount(1);
    expect(".o-autocomplete--dropdown-item .fa-spin").toHaveCount(1);
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

    await contains(".o-autocomplete input").click();
    await runAllTimers();
    await contains(".o-autocomplete input").press("Enter");

    expect(".o-autocomplete input").toHaveCount(1);
    expect(".o-autocomplete input").toHaveValue("");
    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
});

test("press enter on autocomplete with empty source (2)", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`<AutoComplete value="''" sources="sources"/>`;
        static props = [];

        sources = buildSources((/** @type {any} */ request) =>
            request.length > 2 ? [item("test A"), item("test B"), item("test C")] : [],
        );
    }

    await mountWithCleanup(Parent);
    expect(".o-autocomplete input").toHaveCount(1);
    expect(".o-autocomplete input").toHaveValue("");

    await contains(".o-autocomplete input").edit("test", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
    expect(".o-autocomplete .dropdown-menu .o-autocomplete--dropdown-item").toHaveCount(
        3,
    );

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

    await contains(".myButton").hover();
    expect(".o-autocomplete input").toHaveValue("Yolo");

    await contains(".o-autocomplete input").click();
    await runAllTimers();
    await contains(queryFirst(".o-autocomplete--dropdown-item")).click();
    expect(".o-autocomplete input").toHaveValue("My Selection");

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

    await contains(".myButton").hover();
    expect(".o-autocomplete input").toHaveValue("");

    await contains(document.body).click();
    expect(".o-autocomplete input").toHaveValue("");

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
        onSelect(/** @type {any} */ option) {
            this.state.value = option.label;
            expect.step(`select ${option.label}`);
        }
    }
    await mountWithCleanup(Parent);
    expect(".o-autocomplete input").toHaveCount(1);
    await contains(".o-autocomplete input").click();

    let dropdownItemIds = queryAllAttributes(".dropdown-item", "id");
    expect(dropdownItemIds).toHaveLength(2);
    expect(dropdownItemIds[0]).toMatch(/_0_0$/);
    expect(dropdownItemIds[1]).toMatch(/_0_1$/);
    expect(queryAllAttributes(".dropdown-item", "role")).toEqual(["option", "option"]);
    expect(queryAllAttributes(".dropdown-item", "aria-selected")).toEqual([
        "true",
        "false",
    ]);
    expect(".o-autocomplete--input").toHaveAttribute(
        "aria-activedescendant",
        dropdownItemIds[0],
    );

    await contains(".o-autocomplete--input").press("ArrowDown");

    dropdownItemIds = queryAllAttributes(".dropdown-item", "id");
    expect(dropdownItemIds).toHaveLength(2);
    expect(dropdownItemIds[0]).toMatch(/_0_0$/);
    expect(dropdownItemIds[1]).toMatch(/_0_1$/);
    expect(queryAllAttributes(".dropdown-item", "role")).toEqual(["option", "option"]);
    expect(queryAllAttributes(".dropdown-item", "aria-selected")).toEqual([
        "false",
        "true",
    ]);
    expect(".o-autocomplete--input").toHaveAttribute(
        "aria-activedescendant",
        dropdownItemIds[1],
    );

    await contains(".o-autocomplete input").edit("h", { confirm: false });
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
    await contains(".o-autocomplete--dropdown-item:last").click();
    expect.verifySteps(["change", "select Hello"]);
    expect(".o-autocomplete input").toBeFocused();

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

        onSelect(/** @type {any} */ option) {
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
        sources = buildSources((/** @type {any} */ request) =>
            ITEMS.filter(({ label }) => label.startsWith(request)),
        );
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
    await contains(input).click();
    expect(dropdown).toBeVisible();
    await press("Tab");
    await animationFrame();
    expect(dropdown).not.toHaveCount();
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

        onSelect(/** @type {any} */ option) {
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

        onSelect(/** @type {any} */ option) {
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

test("pointerdown on an unselectable option doesn't latch ignoreBlur", async () => {
    class Parent extends Component {
        static template = xml`<AutoComplete value="state.value" sources="sources" selectOnBlur="true"/>`;
        static components = { AutoComplete };
        static props = [];

        state = useState({ value: "" });
        sources = buildSources(() => [
            item("World", this.onSelect.bind(this)),
            { label: "unselectable header" },
        ]);

        onSelect(/** @type {any} */ option) {
            this.state.value = option.label;
            expect.step(option.label);
        }
    }

    await mountWithCleanup(Parent);
    const input = ".o-autocomplete input";
    await contains(input).click();
    expect(".o-autocomplete--dropdown-menu").toBeVisible();

    await pointerDown(".o-autocomplete--dropdown-item:last");
    await pointerUp(document.body);

    queryFirst(input).blur();
    await animationFrame();
    expect(input).toHaveValue("World");
    expect.verifySteps(["World"]);
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
    await contains(".o-autocomplete input").focus();
    await press("ArrowDown");
    await animationFrame();
    expect(".o-autocomplete--dropdown-item").toHaveCount(5);
    expect(isScrollable(dropdownSelector)).toBe(true, {
        message: "dropdown should be scrollable",
    });
    expect(".o-autocomplete--dropdown-item:first-child a").toHaveClass(
        "ui-state-active",
    );
    expect(isInViewWithinScrollableY(activeItemSelector)).toBe(true, {
        message: msgInView,
    });
    expect(
        isInViewWithinScrollableY(".o-autocomplete--dropdown-item:contains('Up')"),
    ).toBe(false, {
        message: "'Up' " + msgNotInView,
    });
    await press("ArrowUp");
    await press("ArrowUp");
    await animationFrame();
    expect(activeItemSelector).toHaveText("Up");
    expect(isInViewWithinScrollableY(activeItemSelector)).toBe(true, {
        message: msgInView,
    });
    expect(
        isInViewWithinScrollableY(".o-autocomplete--dropdown-item:contains('Never')"),
    ).toBe(false, { message: "'Never' " + msgNotInView });
    for (let i = 0; i < 4; i++) {
        await press("ArrowUp");
    }
    await animationFrame();
    expect(activeItemSelector).toHaveText("Never");
    expect(isInViewWithinScrollableY(activeItemSelector)).toBe(true, {
        message: msgInView,
    });
    expect(isInViewWithinScrollableY(".o-autocomplete--dropdown-item:last")).toBe(
        false,
        {
            message: "last " + msgNotInView,
        },
    );
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
            () => [
                item("Hello", () => {}, { id: 1 }),
                item("World", () => {}, { id: 2 }),
            ],
            { optionSlot: "use_this_slot" },
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

        onSelect(/** @type {any} */ option) {
            expect.step(`selected: ${option.label}`);
        }
    }

    await mountWithCleanup(Parent);
    await contains(`.o-autocomplete input`).click();
    const secondOptionId = queryAllAttributes(".dropdown-item", "id")[1];
    expect(`.o-autocomplete--input`).toHaveAttribute(
        "aria-activedescendant",
        secondOptionId,
    );
    expect(`.dropdown-item#${secondOptionId}`).toHaveText("selectable");
    expect(`.dropdown-item#${secondOptionId}`).toHaveAttribute("aria-selected", "true");

    await press("arrowup");
    await animationFrame();
    expect(`.o-autocomplete--input`).not.toHaveAttribute("aria-activedescendant");

    await press("arrowdown");
    await animationFrame();
    expect(`.o-autocomplete--input`).toHaveAttribute(
        "aria-activedescendant",
        secondOptionId,
    );

    await press("arrowdown");
    await animationFrame();
    expect(`.o-autocomplete--input`).not.toHaveAttribute("aria-activedescendant");

    await press("arrowup");
    await animationFrame();
    expect(`.o-autocomplete--input`).toHaveAttribute(
        "aria-activedescendant",
        secondOptionId,
    );

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

test("keyboard navigation skips a loaded-but-empty source", async () => {
    class Parent extends Component {
        static template = xml`<AutoComplete value="''" sources="sources"/>`;
        static components = { AutoComplete };
        static props = [];

        sources = [
            {
                options: () => [
                    item("a", this.onSelect.bind(this)),
                    item("b", this.onSelect.bind(this)),
                ],
            },
            { options: () => [] },
        ];

        onSelect(/** @type {any} */ option) {
            expect.step(`selected: ${option.label}`);
        }
    }

    await mountWithCleanup(Parent);
    await contains(`.o-autocomplete input`).click();
    const [firstOptionId, secondOptionId] = queryAllAttributes(".dropdown-item", "id");
    expect(`.o-autocomplete--input`).toHaveAttribute(
        "aria-activedescendant",
        firstOptionId,
    );

    await press("arrowdown");
    await animationFrame();
    expect(`.o-autocomplete--input`).toHaveAttribute(
        "aria-activedescendant",
        secondOptionId,
    );

    await press("arrowdown");
    await animationFrame();
    expect(`.o-autocomplete--input`).not.toHaveAttribute("aria-activedescendant");

    await press("enter");
    await animationFrame();
    expect.verifySteps([]);

    await press("arrowdown");
    await animationFrame();
    expect(`.o-autocomplete--input`).toHaveAttribute(
        "aria-activedescendant",
        firstOptionId,
    );
    await press("enter");
    await animationFrame();
    expect.verifySteps(["selected: a"]);
});

test.tags("desktop");
test("items are selected only when the mouse moves, not just on enter", async () => {
    class Parent extends Component {
        static template = xml`<AutoComplete value="''" sources="sources"/>`;
        static components = { AutoComplete };
        static props = [];

        sources = buildSources(() => [item("one"), item("two"), item("three")]);
    }

    await mountWithCleanup(Parent);
    queryOne(`.o-autocomplete input`).focus();
    queryOne(`.o-autocomplete input`).click();
    await animationFrame();

    expect(".o-autocomplete--dropdown-item:nth-child(1) .dropdown-item").toHaveClass(
        "ui-state-active",
    );

    await hover(".o-autocomplete--dropdown-item:nth-child(2)");
    await animationFrame();
    expect(
        ".o-autocomplete--dropdown-item:nth-child(2) .dropdown-item",
    ).not.toHaveClass("ui-state-active");

    await press("arrowdown");
    await animationFrame();
    expect(".o-autocomplete--dropdown-item:nth-child(2) .dropdown-item").toHaveClass(
        "ui-state-active",
    );

    await hover(".o-autocomplete--dropdown-item:nth-child(3)");
    await animationFrame();
    expect(
        ".o-autocomplete--dropdown-item:nth-child(2) .dropdown-item",
    ).not.toHaveClass("ui-state-active");
    expect(".o-autocomplete--dropdown-item:nth-child(3) .dropdown-item").toHaveClass(
        "ui-state-active",
    );
});

test.tags("desktop");
test("keyboard-activated option survives a stray mouseleave", async () => {
    class Parent extends Component {
        static template = xml`<AutoComplete value="''" sources="sources"/>`;
        static components = { AutoComplete };
        static props = [];

        sources = buildSources(() => [
            item("one", () => expect.step("one")),
            item("two", () => expect.step("two")),
            item("three", () => expect.step("three")),
        ]);
    }

    await mountWithCleanup(Parent);
    queryOne(`.o-autocomplete input`).focus();
    queryOne(`.o-autocomplete input`).click();
    await animationFrame();

    await press("arrowdown");
    await animationFrame();
    expect(".o-autocomplete--dropdown-item:nth-child(2) .dropdown-item").toHaveClass(
        "ui-state-active",
    );

    queryOne(".o-autocomplete--dropdown-item:nth-child(2)").dispatchEvent(
        new MouseEvent("mouseleave"),
    );
    await animationFrame();
    expect(".o-autocomplete--dropdown-item:nth-child(2) .dropdown-item").toHaveClass(
        "ui-state-active",
    );

    await press("Enter");
    expect.verifySteps(["two"]);
});

test("do not attempt to scroll if element is null", async () => {
    const def = new Deferred();
    class Parent extends Component {
        static template = xml`<AutoComplete value="''" sources="sources" />`;
        static components = { AutoComplete };
        static props = [];

        sources = [
            buildSources(async () => {
                await def;
                return [
                    item("delayed one"),
                    item("delayed two"),
                    item("delayed three"),
                ];
            }),
            buildSources(
                Array.from(Array(20)).map((_, index) => item(`item ${index}`)),
            ),
        ].flat();
    }

    await mountWithCleanup(Parent);
    queryOne(`.o-autocomplete input`).focus();
    queryOne(`.o-autocomplete input`).click();
    await animationFrame();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
    expect(".o-autocomplete .dropdown-item").toHaveCount(21);
    expect(".o-autocomplete .dropdown-item:eq(0)").toHaveClass("o_loading");

    def.resolve();
    await animationFrame();
    expect(".o-autocomplete .dropdown-item").toHaveCount(23);
});

test("a failing source clears its spinner and leaves the other sources usable", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static props = {};
        static template = xml`<AutoComplete value="''" sources="sources"/>`;
        setup() {
            this.sources = [
                {
                    placeholder: "Broken...",
                    options: () => Promise.reject(new Error("source boom")),
                },
                { options: [{ label: "survivor", onSelect: () => {} }] },
            ];
        }
    }
    await mountWithCleanup(Parent);

    expect.errors(1);
    await click(".o-autocomplete--input");
    await animationFrame();
    await animationFrame();
    expect.verifyErrors(["source boom"]);

    expect(".o_loading").toHaveCount(0);
    expect(queryAllTexts(".o-autocomplete--dropdown-item")).toEqual(["survivor"]);
});

test("a failing source does not reject the fire-and-forget open()", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static props = {};
        static template = xml`<AutoComplete value="''" sources="sources"/>`;
        setup() {
            this.sources = [{ options: () => Promise.reject(new Error("nope")) }];
        }
    }
    const parent = await mountWithCleanup(Parent);
    const autocomplete = Object.values(parent.__owl__.children)[0].component;

    expect.errors(1);
    await expect(autocomplete.open(true)).resolves.toBe(undefined);
    await animationFrame();
    expect.verifyErrors(["nope"]);
});

test("a new value prop is applied after the edit was abandoned with Escape", async () => {
    /** @type {(value: string) => void} */
    let setValue;
    class Parent extends Component {
        static components = { AutoComplete };
        static props = {};
        static template = xml`<AutoComplete value="state.value" sources="sources"/>`;
        setup() {
            this.state = useState({ value: "initial" });
            this.sources = [{ options: [{ label: "alpha", onSelect: () => {} }] }];
            setValue = (/** @type {any} */ value) => (this.state.value = value);
        }
    }
    await mountWithCleanup(Parent);
    expect(".o-autocomplete--input").toHaveValue("initial");

    await click(".o-autocomplete--input");
    await edit("typed", { confirm: false });
    await animationFrame();
    await press("Escape");
    await animationFrame();

    setValue("external");
    await animationFrame();

    expect(".o-autocomplete--input").toHaveValue("external");
});

test("a pointerdown inside an iframe dismisses the dropdown", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <div>
                <iframe class="probeFrame" srcdoc="&lt;p&gt;hi&lt;/p&gt;"/>
                <AutoComplete value="'Hello'" sources="sources"/>
            </div>`;
        static props = [];
        sources = buildSources(() => [item("World"), item("Hello")]);
    }

    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").click();
    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);

    const frame = /** @type {HTMLIFrameElement} */ (queryOne("iframe.probeFrame"));
    await new Promise((resolve) => {
        if (frame.contentDocument?.readyState === "complete") {
            resolve(undefined);
        } else {
            frame.addEventListener("load", () => resolve(undefined), { once: true });
        }
    });
    const frameWindow = /** @type {Window & typeof globalThis} */ (frame.contentWindow);
    frameWindow.document.body.dispatchEvent(
        new frameWindow.PointerEvent("pointerdown", { bubbles: true }),
    );
    await animationFrame();

    expect(".o-autocomplete .dropdown-menu").toHaveCount(0);
});

test("two id-less autocompletes do not share generated option ids", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static props = ["*"];
        static template = xml`
            <div>
                <AutoComplete value="''" sources="props.srcs" dropdown="false"/>
                <AutoComplete value="''" sources="props.srcs" dropdown="false"/>
            </div>`;
    }
    await mountWithCleanup(Parent, {
        props: { srcs: [{ options: [{ label: "aa", onSelect: () => {} }] }] },
    });
    await animationFrame();
    const ids = [...document.querySelectorAll("[id]")]
        .map((el) => el.id)
        .filter((id) => id.includes("autocomplete"));
    expect(ids.length).toBeGreaterThan(0);
    expect(new Set(ids).size).toBe(ids.length);
});

test("a source with no selectable option never leaves one active", async () => {
    class Parent extends Component {
        static template = xml`<AutoComplete value="''" sources="sources"/>`;
        static components = { AutoComplete };
        static props = [];
        sources = buildSources(() => [
            { label: "(no result)" },
            { label: "also not selectable" },
        ]);
    }
    await mountWithCleanup(Parent);
    await contains(`.o-autocomplete input`).click();

    expect(".dropdown-item").toHaveCount(2);
    expect(`.o-autocomplete--input`).not.toHaveAttribute("aria-activedescendant");

    for (const key of ["arrowdown", "arrowdown", "arrowup"]) {
        await press(key);
        await animationFrame();
        expect(`.o-autocomplete--input`).not.toHaveAttribute("aria-activedescendant");
    }

    await press("enter");
    await animationFrame();
    expect(".o-autocomplete--dropdown-menu").toHaveCount(1);
});

test("tab does not autoselect after the dropdown was closed and reopened", async () => {
    class Parent extends Component {
        static template = xml`<AutoComplete value="''" sources="sources" autoSelect="true"/>`;
        static components = { AutoComplete };
        static props = [];

        sources = buildSources(() => [
            item("World", () => expect.step("select World")),
            item("Hello", () => expect.step("select Hello")),
        ]);
    }
    await mountWithCleanup(Parent);

    await contains(".o-autocomplete input").click();
    await press("arrowdown");
    await animationFrame();
    await press("escape");
    await animationFrame();
    expect(".o-autocomplete--dropdown-item").toHaveCount(0);

    await contains(".o-autocomplete input").click();
    expect(".o-autocomplete--dropdown-item").toHaveCount(2);
    await press("tab");
    await animationFrame();
    expect.verifySteps([]);
});

test("blur selects the first selectable option, whichever source holds it", async () => {
    class Parent extends Component {
        static template = xml`<AutoComplete value="''" sources="sources" selectOnBlur="true"/>`;
        static components = { AutoComplete };
        static props = [];

        sources = [
            { options: () => [{ label: "(no result)" }] },
            { options: () => [item("World", () => expect.step("select World"))] },
        ];
    }
    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").click();
    expect(queryAllTexts(".o-autocomplete--dropdown-item")).toEqual([
        "(no result)",
        "World",
    ]);

    await contains(document.body).click();
    expect.verifySteps(["select World"]);
});

test("selectOnBlur does not resurrect a suggestion dismissed with escape", async () => {
    class Parent extends Component {
        static template = xml`
            <AutoComplete value="''" sources="sources" selectOnBlur="true"/>
            <button class="elsewhere">elsewhere</button>`;
        static components = { AutoComplete };
        static props = [];

        sources = buildSources(() => [
            item("World", () => expect.step("select World")),
            item("Hello", () => expect.step("select Hello")),
        ]);
    }
    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").click();
    expect(".o-autocomplete--dropdown-item").toHaveCount(2);

    await press("escape");
    await animationFrame();
    expect(".o-autocomplete--dropdown-item").toHaveCount(0);

    await contains(".elsewhere").click();
    expect.verifySteps([]);
});

test("selectOnBlur does not resurrect a suggestion dismissed with tab", async () => {
    class Parent extends Component {
        static template = xml`
            <AutoComplete value="''" sources="sources" selectOnBlur="true"/>
            <button class="elsewhere">elsewhere</button>`;
        static components = { AutoComplete };
        static props = [];

        sources = buildSources(() => [
            item("World", () => expect.step("select World")),
        ]);
    }
    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").click();
    expect(".o-autocomplete--dropdown-item").toHaveCount(1);

    await press("tab");
    await animationFrame();
    expect(".o-autocomplete--dropdown-item").toHaveCount(0);

    await contains(".elsewhere").click();
    expect.verifySteps([]);
});

test("reopening after a dismissal restores selectOnBlur", async () => {
    class Parent extends Component {
        static template = xml`
            <AutoComplete value="''" sources="sources" selectOnBlur="true"/>
            <button class="elsewhere">elsewhere</button>`;
        static components = { AutoComplete };
        static props = [];

        sources = buildSources(() => [
            item("World", () => expect.step("select World")),
        ]);
    }
    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").click();
    await press("escape");
    await animationFrame();

    await contains(".o-autocomplete input").click();
    expect(".o-autocomplete--dropdown-item").toHaveCount(1);
    await contains(".elsewhere").click();
    expect.verifySteps(["select World"]);
});

test.tags("desktop");
test("arrowup on a closed dropdown enters the list from the bottom", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`<AutoComplete value="''" sources="sources"/>`;
        static props = [];

        sources = buildSources(() => [item("A"), item("B"), item("C")]);
    }
    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").focus();
    await press("ArrowUp");
    await runAllTimers();
    await animationFrame();
    expect(".o-autocomplete--dropdown-item").toHaveCount(3);
    expect(".o-autocomplete--dropdown-item .ui-state-active").toHaveText("C");
});

test.tags("desktop");
test("arrowup still enters from the bottom after the list has been closed", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`<AutoComplete value="''" sources="sources"/>`;
        static props = [];

        sources = buildSources(() => [item("A"), item("B"), item("C")]);
    }
    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").focus();
    await press("ArrowDown");
    await runAllTimers();
    await animationFrame();
    expect(".o-autocomplete--dropdown-item .ui-state-active").toHaveText("A");

    await press("Escape");
    await animationFrame();
    expect(".o-autocomplete--dropdown-menu").toHaveCount(0);

    await press("ArrowUp");
    await runAllTimers();
    await animationFrame();
    expect(".o-autocomplete--dropdown-item .ui-state-active").toHaveText("C");
});

test.tags("desktop");
test("menuPositionOptions is followed after it changes", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <div style="height: 400px"/>
            <AutoComplete value="''" sources="sources" menuPositionOptions="state.opts"/>`;
        static props = [];

        state = useState({ opts: { position: "bottom-start" } });
        sources = buildSources(() => [item("A")]);
    }
    const parent = await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").click();
    await runAllTimers();
    await animationFrame();
    let input = queryRect(".o-autocomplete input");
    let menu = queryRect(".o-autocomplete--dropdown-menu");
    expect(menu.top >= input.bottom - 1).toBe(true, {
        message: "baseline: the menu opens below the input",
    });

    await contains(".o-autocomplete input").click();
    await animationFrame();
    parent.state.opts = { position: "top-start" };
    await animationFrame();

    await contains(".o-autocomplete input").click();
    await runAllTimers();
    await animationFrame();
    input = queryRect(".o-autocomplete input");
    menu = queryRect(".o-autocomplete--dropdown-menu");
    expect(menu.bottom <= input.top + 1).toBe(true, {
        message: "the menu now opens above the input",
    });
});

test("selectOnBlur does not commit an option the parent already superseded", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <AutoComplete value="state.value" sources="sources" selectOnBlur="true"/>
            <button class="elsewhere">elsewhere</button>`;
        static props = [];

        state = useState({ value: "" });
        sources = buildSources(() => [
            item("World", () => expect.step("select World")),
            item("Hello", () => expect.step("select Hello")),
        ]);
    }
    const parent = await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").click();
    expect(".o-autocomplete--dropdown-item").toHaveCount(2);

    parent.state.value = "Something else";
    await animationFrame();
    expect(".o-autocomplete--dropdown-menu").toHaveCount(0);

    await contains(".elsewhere").click();
    expect.verifySteps([]);
});

test("selectOnBlur survives a parent that resets its value while typing", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <AutoComplete value="state.chosen?.label ?? ''" sources="sources"
                          onInput.bind="onInput" selectOnBlur="true" autoSelect="true"/>
            <button class="elsewhere">elsewhere</button>`;
        static props = [];

        state = useState({ chosen: { label: "Restaurant" } });
        onInput() {
            this.state.chosen = undefined;
        }
        sources = buildSources(() => [
            item("Bakery", () => expect.step("select Bakery")),
        ]);
    }
    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").edit("ba", { confirm: false });
    await runAllTimers();
    await animationFrame();

    await contains(".elsewhere").click();
    expect.verifySteps(["select Bakery"]);
});

test("tab commits after a parent reset its value while typing", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <AutoComplete value="state.chosen?.label ?? ''" sources="sources"
                          onInput.bind="onInput" selectOnBlur="true" autoSelect="true"/>
            <button class="elsewhere">elsewhere</button>`;
        static props = [];

        state = useState({ chosen: { label: "Restaurant" } });
        onInput() {
            this.state.chosen = undefined;
        }
        sources = buildSources(() => [
            item("Bakery", () => expect.step("select Bakery")),
        ]);
    }
    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").edit("ba", { confirm: false });
    await runAllTimers();
    await animationFrame();
    await press("Tab");
    await animationFrame();
    expect.verifySteps(["select Bakery"]);
});

test.tags("desktop");
test("an arrow-opened list counts as browsed for the tab commit", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`
            <AutoComplete value="''" sources="sources" autoSelect="true"/>
            <button class="elsewhere">x</button>`;
        static props = [];

        sources = buildSources(() => [
            item("A", () => expect.step("A")),
            item("B", () => expect.step("B")),
        ]);
    }
    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").focus();
    await press("ArrowDown");
    await runAllTimers();
    await animationFrame();
    expect(".o-autocomplete--dropdown-item .ui-state-active").toHaveText("A");
    await press("Tab");
    await animationFrame();
    expect.verifySteps(["A"]);
});

test.tags("desktop");
test("an arrowup-opened list commits its last option on tab", async () => {
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`<AutoComplete value="''" sources="sources" autoSelect="true"/>`;
        static props = [];

        sources = buildSources(() => [
            item("A", () => expect.step("A")),
            item("C", () => expect.step("C")),
        ]);
    }
    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").focus();
    await press("ArrowUp");
    await runAllTimers();
    await animationFrame();
    await press("Tab");
    await animationFrame();
    expect.verifySteps(["C"]);
});

test("a loading source does not present itself as a selected option", async () => {
    const def = new Deferred();
    class Parent extends Component {
        static components = { AutoComplete };
        static props = {};
        static template = xml`<AutoComplete value="''" sources="sources"/>`;

        sources = [
            {
                placeholder: "Loading...",
                options: async () => {
                    await def;
                    return [item("done")];
                },
            },
        ];
    }
    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").click();
    await animationFrame();
    expect(".o-autocomplete .o_loading").toHaveCount(1);

    expect(".o-autocomplete input").not.toHaveAttribute("aria-activedescendant");
    expect(
        queryAll('.o-autocomplete [role="option"][aria-selected="true"]'),
    ).toHaveLength(0);
    expect(".o-autocomplete--dropdown-menu").toHaveAttribute("aria-busy", "true");

    def.resolve();
    await animationFrame();
    expect(".o-autocomplete .o_loading").toHaveCount(0);
    expect(".o-autocomplete--dropdown-menu").not.toHaveAttribute("aria-busy");
});

test("a dropdown list is not in the tab order", async () => {
    class Parent extends Component {
        static template = xml`
            <div>
                <AutoComplete value="''" sources="sources"/>
                <button class="after">after</button>
            </div>`;
        static components = { AutoComplete };
        static props = [];
        sources = buildSources(() => [item("World"), item("Hello")]);
    }
    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").click();
    expect(".o-autocomplete--dropdown-menu").toHaveCount(1);

    await press("Tab");
    expect(document.activeElement).toBe(queryOne("button.after"));
});

test("an inline list is reachable by tab", async () => {
    class Parent extends Component {
        static template = xml`
            <div>
                <AutoComplete value="''" sources="sources" dropdown="false"/>
                <button class="after">after</button>
            </div>`;
        static components = { AutoComplete };
        static props = [];
        sources = buildSources(() => [item("World"), item("Hello")]);
    }
    await mountWithCleanup(Parent);
    await contains(".o-autocomplete input").click();

    await press("Tab");
    expect(document.activeElement).toBe(
        queryOne(".o-autocomplete--dropdown-item:first-child a"),
    );
});

test("typing does not render the component until the debounced search opens the list", async () => {
    let renders = 0;
    patchWithCleanup(AutoComplete.prototype, {
        setup() {
            super.setup();
            onRendered(() => renders++);
        },
    });
    class Parent extends Component {
        static components = { AutoComplete };
        static template = xml`<AutoComplete value="'Hello'" sources="sources"/>`;
        static props = [];
        sources = buildSources(() => [item("World"), item("Hello")]);
    }
    await mountWithCleanup(Parent);
    expect(".o-autocomplete input").toHaveValue("Hello");
    const mounted = renders;

    await contains(".o-autocomplete input").fill("abc", { confirm: false });
    await animationFrame();
    expect(renders).toBe(mounted, {
        message: "three keystrokes render nothing: the input owns its value",
    });
    expect(".o-autocomplete input").toHaveValue("abc");

    await runAllTimers();
    expect(".o-autocomplete .dropdown-menu").toHaveCount(1);
    expect(renders).toBe(mounted + 1, {
        message: "the debounced search renders once, with the loaded options",
    });
});

for (const outcome of ["resolve", "reject"]) {
    test(`destroying autocomplete completes a pending open before its source can ${outcome}`, async () => {
        const loaded = new Deferred();
        const autocomplete = await mountWithCleanup(AutoComplete, {
            props: { sources: [{ options: () => loaded }] },
        });
        patchWithCleanup(autocomplete, {
            reportSourceError: () => expect.step("late error"),
        });
        let finished = false;
        autocomplete.open().then(() => {
            finished = true;
        });
        autocomplete.__owl__.app.destroy();
        await animationFrame();
        expect(finished).toBe(true);
        if (outcome === "resolve") {
            loaded.resolve([{ label: "Late option" }]);
        } else {
            loaded.reject(new Error("late source failure"));
        }
        await animationFrame();
        expect.verifySteps([]);
    });
}

test("waiting for current options does not focus an input destroyed during the wait", async () => {
    const autocomplete = await mountWithCleanup(AutoComplete, {
        props: { sources: [] },
    });
    const loaded = new Deferred();
    autocomplete._loadedRequest = "old";
    autocomplete.inputRef.el.value = "new";
    autocomplete.loadingPromise = loaded;
    const clicked = autocomplete.onOptionClick({});
    autocomplete.__owl__.app.destroy();
    loaded.resolve();
    await clicked;
    expect(autocomplete.inputRef.el).toBe(null);
});
